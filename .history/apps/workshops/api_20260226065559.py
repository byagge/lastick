from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.operations.workshops.models import Workshop, NeutralBatch
from apps.employee_tasks.models import EmployeeTask
from apps.inventory.models import EmployeeMaterialBalance
from apps.services.models import Service
from apps.defects.models import Defect
from apps.orders.models import OrderItem
from apps.products.models import Product

User = get_user_model()


def _is_extrusion_workshop(workshop: Workshop) -> bool:
    if not workshop:
        return False
    name = (workshop.name or "").lower()
    return 'экструз' in name or 'экстуз' in name


def _is_packaging_workshop(workshop: Workshop) -> bool:
    if not workshop:
        return False
    name = (workshop.name or "").lower()
    return 'пакет' in name or 'пакето' in name or 'упаков' in name


class MyWorkshopsView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		# Получаем цеха, которыми управляет пользователь (главный мастер или дополнительный)
		workshops = []
		
		# Цеха, где пользователь является главным мастером
		managed_workshops = request.user.operation_managed_workshops.all()
		for workshop in managed_workshops:
			workshops.append({
				'id': workshop.id, 
				'name': workshop.name,
				'role': 'main_manager'
			})
		
		# Цеха, где пользователь является дополнительным мастером
		additional_workshops = request.user.workshop_master_roles.filter(is_active=True).select_related('workshop')
		for workshop_master in additional_workshops:
			workshops.append({
				'id': workshop_master.workshop.id, 
				'name': workshop_master.workshop.name,
				'role': 'additional_master'
			})
		
		return Response(workshops)

class WorkshopEmployeesView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		workshop_id = request.GET.get('workshop')
		employees = User.objects.filter(workshop_id=workshop_id)
		return Response([{'id': e.id, 'name': e.get_full_name()} for e in employees])

class AllWorkshopsView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		workshops = Workshop.objects.filter(is_active=True).order_by('name', 'id')
		workshops_data = []
		
		for workshop in workshops:
			# Получаем всех мастеров цеха
			all_masters = workshop.get_all_masters()
			master_info = []
			
			# Главный мастер
			if workshop.manager:
				master_info.append({
					'id': workshop.manager.id,
					'name': workshop.manager.get_full_name(),
					'role': 'main_manager'
				})
			
			# Дополнительные мастера
			additional_masters = workshop.workshop_masters.filter(is_active=True).select_related('master')
			for wm in additional_masters:
				master_info.append({
					'id': wm.master.id,
					'name': wm.master.get_full_name(),
					'role': 'additional_master'
				})
			
			workshops_data.append({
				'id': workshop.id,
				'name': workshop.name,
				'masters': master_info,
				'master_count': len(master_info)
			})
		
		return Response(workshops_data)

class WorkshopMastersView(APIView):
	permission_classes = [IsAuthenticated]
	def get(self, request):
		"""Получает список всех мастеров конкретного цеха"""
		workshop_id = request.GET.get('workshop')
		if not workshop_id:
			return Response({'error': 'Не указан ID цеха'}, status=400)
		
		try:
			workshop = Workshop.objects.get(id=workshop_id, is_active=True)
		except Workshop.DoesNotExist:
			return Response({'error': 'Цех не найден'}, status=404)
		
		# Получаем всех мастеров цеха
		all_masters = workshop.get_all_masters()
		masters_data = []
		
		# Главный мастер
		if workshop.manager:
			masters_data.append({
				'id': workshop.manager.id,
				'name': workshop.manager.get_full_name(),
				'role': 'main_manager',
				'can_remove': False
			})
		
		# Дополнительные мастера
		additional_masters = workshop.workshop_masters.filter(is_active=True).select_related('master')
		for wm in additional_masters:
			masters_data.append({
				'id': wm.master.id,
				'name': wm.master.get_full_name(),
				'role': 'additional_master',
				'can_remove': True,
				'added_at': wm.added_at,
				'notes': wm.notes
			})
		
		return Response(masters_data)

class AddWorkshopMasterView(APIView):
	permission_classes = [IsAuthenticated]
	def post(self, request):
		"""Добавляет дополнительного мастера к цеху"""
		workshop_id = request.data.get('workshop_id')
		master_id = request.data.get('master_id')
		
		if not workshop_id or not master_id:
    	    return Response({'error': 'Не указаны ID цеха или мастера'}, status=400)
		
		try:
			workshop = Workshop.objects.get(id=workshop_id, is_active=True)
			master = User.objects.get(id=master_id)
		except (Workshop.DoesNotExist, User.DoesNotExist):
			return Response({'error': 'Цех или мастер не найден'}, status=404)
		
		# Проверяем права доступа (только главный мастер может добавлять других мастеров)
		if not workshop.is_user_master(request.user) or workshop.manager != request.user:
			return Response({'error': 'Недостаточно прав для добавления мастера'}, status=403)
		
		# Добавляем мастера
		success, message = workshop.add_master(master)
		
		if success:
			return Response({'message': message, 'success': True})
		else:
			return Response({'error': message}, status=400)

class RemoveWorkshopMasterView(APIView):
	permission_classes = [IsAuthenticated]
	def post(self, request):
		"""Удаляет дополнительного мастера из цеха"""
		workshop_id = request.data.get('workshop_id')
		master_id = request.data.get('master_id')
		
		if not workshop_id or not master_id:
			return Response({'error': 'Не указаны ID цеха или мастера'}, status=400)
		
		try:
			workshop = Workshop.objects.get(id=workshop_id, is_active=True)
			master = User.objects.get(id=master_id)
		except (Workshop.DoesNotExist, User.DoesNotExist):
			return Response({'error': 'Цех или мастер не найден'}, status=404)
		
		# Проверяем права доступа (только главный мастер может удалять других мастеров)
		if not workshop.is_user_master(request.user) or workshop.manager != request.user:
			return Response({'error': 'Недостаточно прав для удаления мастера'}, status=403)
		
		# Удаляем мастера
		success, message = workshop.remove_master(master)
		
		if success:
			return Response({'message': message, 'success': True})
		else:
			return Response({'error': message}, status=400) 

class MasterWorkshopsStatsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получает статистику по всем цехам мастера"""
        user = request.user
        
        # Получаем все цеха мастера
        master_workshops = []
        
        # Цеха, где пользователь является главным мастером
        managed_workshops = user.operation_managed_workshops.filter(is_active=True)
        for workshop in managed_workshops:
            master_workshops.append(workshop)
        
        # Цеха, где пользователь является дополнительным мастером
        additional_workshops = user.workshop_master_roles.filter(is_active=True, workshop__is_active=True).select_related('workshop')
        for workshop_master in additional_workshops:
            master_workshops.append(workshop_master.workshop)
        
        # Убираем дубликаты
        master_workshops = list(set(master_workshops))
        
        # Периоды для статистики
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Общая статистика по всем цехам мастера
        total_stats = self._calculate_total_stats(master_workshops, week_ago, month_ago)
        
        # Статистика по каждому цеху
        workshops_stats = []
        for workshop in master_workshops:
            workshop_stats = self._calculate_workshop_stats(workshop, week_ago, month_ago)
            workshops_stats.append(workshop_stats)
        
        return Response({
            'total_stats': total_stats,
            'workshops': workshops_stats
        })
    
    def _calculate_total_stats(self, workshops, week_ago, month_ago):
        """Рассчитывает общую статистику по всем цехам мастера"""
        # Получаем все задачи по цехам мастера
        workshop_ids = [w.id for w in workshops]
        all_tasks = EmployeeTask.objects.filter(stage__workshop_id__in=workshop_ids)
        
        # Статистика за неделю
        week_tasks = all_tasks.filter(created_at__gte=week_ago)
        week_completed = week_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Статистика за месяц
        month_tasks = all_tasks.filter(created_at__gte=month_ago)
        month_completed = month_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Общая статистика
        total_completed = all_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Количество сотрудников
        total_employees = sum(w.users.count() for w in workshops)
        
        # Эффективность (процент выполненных задач без брака)
        total_quantity = all_tasks.aggregate(total=Sum('quantity'))['total'] or 0
        total_completed_quantity = total_completed['total'] or 0
        total_defects = total_completed['defects'] or 0
        
        efficiency = 0
        if total_quantity > 0:
            efficiency = round(((total_completed_quantity - total_defects) / total_quantity) * 100, 1)
        
        return {
            'total_workshops': len(workshops),
            'total_employees': total_employees,
            'week_stats': {
                'completed_works': week_completed['total'] or 0,
                'defects': week_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(week_completed['total'] or 0, week_completed['defects'] or 0)
            },
            'month_stats': {
                'completed_works': month_completed['total'] or 0,
                'defects': month_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(month_completed['total'] or 0, month_completed['defects'] or 0)
            },
            'total_stats': {
                'completed_works': total_completed_quantity,
                'defects': total_defects,
                'efficiency': efficiency
            }
        }
    
    def _calculate_workshop_stats(self, workshop, week_ago, month_ago):
        """Рассчитывает статистику по конкретному цеху"""
        # Получаем задачи цеха
        workshop_tasks = EmployeeTask.objects.filter(stage__workshop=workshop)
        
        # Статистика за неделю
        week_tasks = workshop_tasks.filter(created_at__gte=week_ago)
        week_completed = week_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Статистика за месяц
        month_tasks = workshop_tasks.filter(created_at__gte=month_ago)
        month_completed = month_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Общая статистика
        total_completed = workshop_tasks.aggregate(
            total=Sum('completed_quantity'),
            defects=Sum('defective_quantity')
        )
        
        # Количество сотрудников
        employees_count = workshop.users.count()
        
        # Эффективность
        total_quantity = workshop_tasks.aggregate(total=Sum('quantity'))['total'] or 0
        total_completed_quantity = total_completed['total'] or 0
        total_defects = total_completed['defects'] or 0
        
        efficiency = 0
        if total_quantity > 0:
            efficiency = round(((total_completed_quantity - total_defects) / total_quantity) * 100, 1)
        
        return {
            'id': workshop.id,
            'name': workshop.name,
            'description': workshop.description,
            'employees_count': employees_count,
            'week_stats': {
                'completed_works': week_completed['total'] or 0,
                'defects': week_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(week_completed['total'] or 0, week_completed['defects'] or 0)
            },
            'month_stats': {
                'completed_works': month_completed['total'] or 0,
                'defects': month_completed['defects'] or 0,
                'efficiency': self._calculate_efficiency(month_completed['total'] or 0, month_completed['defects'] or 0)
            },
            'total_stats': {
                'completed_works': total_completed_quantity,
                'defects': total_defects,
                'efficiency': efficiency
            }
        }
    
		def _calculate_efficiency(self, completed, defects):
        """Рассчитывает эффективность в процентах"""
		if completed == 0:
			return 0
		return round(((completed - defects) / completed) * 100, 1)


class ExtrusionReportView(APIView):
    """
    Workflow для первого (экструзионного) цеха.

    POST:
      - читает баланс материалов сотрудника;
      - считает произведённый объём, брак и эффективность;
      - создаёт партию в нейтральной зоне;
      - создаёт запись брака в системе defects;
      - считает заработок для сотрудников с оплатой 'variable'.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        workshop = getattr(user, "workshop", None)

        if not workshop or not _is_extrusion_workshop(workshop):
            return Response(
                {"detail": "Этот workflow доступен только для экструзионного цеха."},
                status=400,
            )

        try:
            produced_raw = request.data.get("produced_quantity")
            produced_quantity = Decimal(str(produced_raw or "0"))
        except Exception:
            return Response(
                {"detail": "Некорректное значение produced_quantity."}, status=400
            )

        if produced_quantity <= 0:
            return Response(
                {"detail": "Нужно указать положительное количество произведённого товара."},
                status=400,
            )

        with transaction.atomic():
            balances = (
                EmployeeMaterialBalance.objects.select_for_update()
                .filter(employee=user)
                .select_related("material")
            )
            total_material = sum((b.quantity or 0) for b in balances)

            if total_material <= 0:
                return Response(
                    {
                        "detail": "У вас нет материалов в балансе. Возьмите материалы на складе.",
                        "has_balance": False,
                    },
                    status=400,
                )

            total_material = Decimal(str(total_material))
            if produced_quantity > total_material:
                produced_quantity = total_material

            scrap_quantity = total_material - produced_quantity
            efficiency = (
                float((produced_quantity / total_material) * Decimal("100"))
                if total_material > 0
                else 0.0
            )

            # Обнуляем баланс материалов сотрудника — всё ушло либо в продукт, либо в брак
            for b in balances:
                b.quantity = 0
                b.save(update_fields=["quantity"])

            # Создаём партию в нейтральной зоне для второго цеха
            neutral_batch = NeutralBatch.objects.create(
                workshop=workshop,
                employee=user,
                total_quantity=produced_quantity,
            )

            # Создаём запись брака в новой системе дефектов (одна запись, с количеством в комментарии)
            defect = None
            if scrap_quantity > 0:
                defect = Defect.objects.create(
                    employee_task=None,
                    product=None,
                    user=user,
                    status=Defect.DefectStatus.PENDING,
                    master_comment=f"Брак экструзии: {scrap_quantity} ед. из {total_material} ед.",
                )

            # Расчёт заработка для сдельной оплаты: ставка берётся из первой активной услуги цеха
            earnings = Decimal("0")
            if getattr(user, "payment_type", None) == User.PaymentType.VARIABLE:
                service = (
                    Service.objects.filter(workshop=workshop, is_active=True)
                    .order_by("id")
                    .first()
                )
                rate = service.service_price if service else Decimal("0")
                earnings = (produced_quantity * Decimal(str(rate or 0))).quantize(
                    Decimal("0.01")
                )
                if earnings > 0:
                    user.add_to_balance(earnings)

        return Response(
            {
                "status": "success",
                "has_balance": True,
                "produced_quantity": float(produced_quantity),
                "total_material": float(total_material),
                "scrap_quantity": float(scrap_quantity),
                "efficiency": efficiency,
                "earnings": float(earnings),
                "neutral_batch_id": neutral_batch.id,
                "defect_id": defect.id if defect else None,
            }
        )


class NeutralBatchesListView(APIView):
    """
    Список доступных партий нейтральной зоны для второго цеха.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        batches = (
            NeutralBatch.objects.select_related("workshop", "employee")
            .all()
            .order_by("-created_at")
        )
        data = []
        for b in batches:
            available = b.available_quantity
            if available <= 0:
                continue
            data.append(
                {
                    "id": b.id,
                    "workshop_id": b.workshop_id,
                    "workshop_name": b.workshop.name,
                    "employee_id": b.employee_id,
                    "employee_name": b.employee.get_full_name(),
                    "total_quantity": float(b.total_quantity),
                    "used_quantity": float(b.used_quantity),
                    "available_quantity": float(available),
                    "created_at": b.created_at.isoformat(),
                }
            )
        return Response(data)


class PackagingReportView(APIView):
    """
    Workflow для второго (пакетоотделочного) цеха.

    POST:
      - принимает ID партии нейтральной зоны и режим работы:
        * по заявке: order_item_id (позиция заявки);
        * на запас: без заявки;
      - считает выпуск, брак, эффективность;
      - создаёт запись в складе готовой продукции и обновляет позицию заявки.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        workshop = getattr(user, "workshop", None)

        if not workshop or not _is_packaging_workshop(workshop):
            return Response(
                {"detail": "Этот workflow доступен только для пакетоотделочного/упаковочного цеха."},
                status=400,
            )

        batch_id = request.data.get("neutral_batch_id")
        if not batch_id:
            return Response({"detail": "neutral_batch_id обязателен."}, status=400)

        try:
            produced_raw = request.data.get("produced_quantity")
            produced_quantity = Decimal(str(produced_raw or "0"))
        except Exception:
            return Response(
                {"detail": "Некорректное значение produced_quantity."}, status=400
            )

        if produced_quantity <= 0:
            return Response(
                {"detail": "Нужно указать положительное количество произведённого товара."},
                status=400,
            )

        mode = (request.data.get("mode") or "order").lower()
        order_item_id = request.data.get("order_item_id")
        product_id = request.data.get("product_id")

        with transaction.atomic():
            batch = NeutralBatch.objects.select_for_update().get(pk=batch_id)
            available = batch.available_quantity
            if available <= 0:
                return Response(
                    {"detail": "У выбранной партии нет доступного объёма."},
                    status=400,
                )

            total_input = available
            if produced_quantity > total_input:
                produced_quantity = total_input

            scrap_quantity = total_input - produced_quantity
            efficiency = (
                float((produced_quantity / total_input) * Decimal("100"))
                if total_input > 0
                else 0.0
            )

            # Списываем всю доступную партию в работу второго цеха
            batch.consume(total_input)

            order_item = None
            order = None
            product = None

            if mode == "order":
                if not order_item_id:
                    return Response(
                        {"detail": "order_item_id обязателен при работе по заявке."},
                        status=400,
                    )
                try:
                    order_item = OrderItem.objects.select_for_update().get(pk=order_item_id)
                except OrderItem.DoesNotExist:
                    return Response(
                        {"detail": "Указанная позиция заявки не найдена."},
                        status=404,
                    )
                order = order_item.order
                product = order_item.product
                # Обновляем прогресс по заявке
                order_item.packaging_received_quantity = (
                    (order_item.packaging_received_quantity or 0) + int(produced_quantity)
                )
                order_item.save(update_fields=["packaging_received_quantity"])
            else:  # режим "stock" / на запас
                if not product_id:
                    return Response(
                        {"detail": "product_id обязателен при работе на запас."},
                        status=400,
                    )
                try:
                    product = Product.objects.get(pk=product_id)
                except Product.DoesNotExist:
                    return Response(
                        {"detail": "Указанный товар (product_id) не найден."},
                        status=404,
                    )

            # Создаём запись в складе готовой продукции
            from apps.finished_goods.models import FinishedGood

            finished = FinishedGood.objects.create(
                product=product,
                order_item=order_item,
                order=order,
                quantity=int(produced_quantity),
                workshop=workshop,
                status="stock",
            )

            # Запись брака
            defect = None
            if scrap_quantity > 0:
                defect = Defect.objects.create(
                    employee_task=None,
                    product=product,
                    user=user,
                    status=Defect.DefectStatus.PENDING,
                    master_comment=f"Брак второго цеха: {scrap_quantity} ед. из {total_input} ед.",
                )

            # Заработок для сдельной оплаты
            earnings = Decimal("0")
            if getattr(user, "payment_type", None) == User.PaymentType.VARIABLE:
                service = (
                    Service.objects.filter(workshop=workshop, is_active=True)
                    .order_by("id")
                    .first()
                )
                rate = service.service_price if service else Decimal("0")
                earnings = (produced_quantity * Decimal(str(rate or 0))).quantize(
                    Decimal("0.01")
                )
                if earnings > 0:
                    user.add_to_balance(earnings)

        return Response(
            {
                "status": "success",
                "mode": mode,
                "produced_quantity": float(produced_quantity),
                "input_quantity": float(total_input),
                "scrap_quantity": float(scrap_quantity),
                "efficiency": efficiency,
                "earnings": float(earnings),
                "finished_good_id": finished.id,
                "defect_id": defect.id if defect else None,
                "order_id": order.id if order else None,
                "order_item_id": order_item.id if order_item else None,
            }
        )