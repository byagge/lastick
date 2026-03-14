from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from .models import FinishedGood, FinishedGoodSale
from .serializers import FinishedGoodSerializer, FinishedGoodDetailSerializer, FinishedGoodSaleSerializer
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.db import transaction
from django.utils import timezone
from apps.defects.models import Defect
from datetime import timedelta
import re

# Create your views here.

class FinishedGoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FinishedGood.objects.select_related(
        'product', 'order', 'workshop', 'costing'
    ).prefetch_related(
        'costing__labor_costs__employee_task__employee',
        'costing__labor_costs__employee_task__stage__workshop',
        'costing__material_costs__material_consumption__material',
        'costing__material_costs__material_consumption__workshop',
    ).all().order_by('-received_at')
    serializer_class = FinishedGoodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # DRF при включённой пагинации возвращает структуру
        # {"count": ..., "next": ..., "previous": ..., "results": [...]}
        # поэтому достаём именно список записей
        data = response.data
        items = data.get('results', data) if isinstance(data, dict) else data

        # Добавляем информацию о браках для каждой записи
        for item in items:
            # На всякий случай пропускаем некорректные элементы
            if not isinstance(item, dict):
                continue

            finished_good_id = item.get('id')
            if not finished_good_id:
                continue
            
            try:
                finished_good = FinishedGood.objects.get(id=finished_good_id)
            except FinishedGood.DoesNotExist:
                continue
            
            # Ищем связанный брак для этой готовой продукции
            # Брак создается в тот же день с комментарием об упаковке
            item_date = finished_good.received_at or finished_good.packaging_date
            if not item_date:
                continue
                
            date_start = item_date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            # Ищем брак по продукту и дате, или по комментарию
            # Приоритет: продукт + дата, затем только дата + комментарий
            related_defect = None
            
            # Сначала пытаемся найти по продукту и дате
            if finished_good.product:
                related_defect = Defect.objects.filter(
                    product=finished_good.product,
                    created_at__gte=date_start,
                    created_at__lt=date_end,
                    employee_comment__icontains="Packaging defect"
                ).first()
            
            # Если не нашли, ищем только по дате и комментарию (может быть несколько, берем первый)
            if not related_defect:
                related_defect = Defect.objects.filter(
                    created_at__gte=date_start,
                    created_at__lt=date_end,
                    employee_comment__icontains="Packaging defect"
                ).order_by('-created_at').first()
            
            scrap_quantity = 0
            input_quantity = float(finished_good.quantity)
            
            if related_defect:
                scrap_quantity = float(related_defect.quantity)
                # Из комментария "Packaging defect: X kg of Y kg" извлекаем Y
                comment = related_defect.employee_comment or ""
                match = re.search(r"of\s+([\d.]+)\s+kg", comment)
                if match:
                    input_quantity = float(match.group(1))
                else:
                    # Если не удалось извлечь, считаем что input = produced + scrap
                    input_quantity = float(finished_good.quantity) + scrap_quantity
            
            efficiency = (float(finished_good.quantity) / input_quantity * 100) if input_quantity > 0 else 100.0
            
            item['input_quantity'] = input_quantity
            item['scrap_quantity'] = scrap_quantity
            item['efficiency'] = round(efficiency, 1)
            item['defect_id'] = related_defect.id if related_defect else None
        
        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = FinishedGoodDetailSerializer(instance, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='recalculate-cost')
    def recalculate_cost(self, request, pk=None):
        """
        Пересчитывает себестоимость для конкретной готовой продукции.
        """
        finished_good = self.get_object()
        
        if not finished_good.order:
            return Response(
                {'error': 'Нельзя рассчитать себестоимость без связанного заказа'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = finished_good.calculate_actual_cost(save=True)
            if result is None:
                return Response(
                    {'error': 'Не удалось рассчитать себестоимость. Проверьте наличие связанных задач и расходов сырья.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Обновляем объект из БД для получения актуальных данных
            finished_good.refresh_from_db()
            serializer = FinishedGoodDetailSerializer(finished_good, context={'request': request})
            
            return Response({
                'message': 'Себестоимость успешно пересчитана',
                'costing': result,
                'finished_good': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка пересчета себестоимости для FinishedGood #{finished_good.id}: {e}", exc_info=True)
            return Response(
                {'error': f'Ошибка при пересчете себестоимости: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='recalculate-all-costs')
    def recalculate_all_costs(self, request):
        """
        Пересчитывает себестоимость для всех товаров на складе (status='stock').
        """
        finished_goods = FinishedGood.objects.filter(status='stock', order__isnull=False)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for fg in finished_goods:
            try:
                result = fg.calculate_actual_cost(save=True)
                if result is not None:
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(f"FinishedGood #{fg.id}: нет связанных данных")
            except Exception as e:
                error_count += 1
                errors.append(f"FinishedGood #{fg.id}: {str(e)}")
        
        return Response({
            'message': f'Пересчет завершен. Успешно: {success_count}, Ошибок: {error_count}',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10]  # Ограничиваем количество ошибок в ответе
        }, status=status.HTTP_200_OK)


class FinishedGoodSaleViewSet(viewsets.ModelViewSet):
    queryset = FinishedGoodSale.objects.select_related(
        'finished_good__product',
        'client',
        'order'
    ).all()
    serializer_class = FinishedGoodSaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            sale = serializer.save()
            finished_good = sale.finished_good
            sale_qty = int(getattr(sale, 'quantity', 0) or 0)
            remaining = int(finished_good.quantity or 0) - sale_qty
            if remaining < 0:
                raise ValidationError('Количество продажи больше доступного остатка.')
            if remaining == 0:
                finished_good.status = 'issued'
                finished_good.issued_at = timezone.now()
                finished_good.recipient = sale.client.name
                if sale.order:
                    finished_good.order = sale.order
                finished_good.save(update_fields=['status', 'issued_at', 'recipient', 'order'])
            else:
                finished_good.quantity = remaining
                finished_good.status = 'stock'
                finished_good.issued_at = None
                finished_good.recipient = ''
                finished_good.save(update_fields=['quantity', 'status', 'issued_at', 'recipient'])

            # Автоматически создаем доход "С продаж" в finance при продаже готовой продукции.
            # Защита от дублей: используем уникальную ссылку в order_reference.
            from apps.finance.models import Income
            order_reference = f"FGSALE:{sale.pk}"
            if not Income.objects.filter(order_reference=order_reference).exists():
                product_name = getattr(getattr(finished_good, 'product', None), 'name', None) or str(getattr(finished_good, 'product', ''))
                qty = sale_qty or 0
                order_name = getattr(getattr(sale, 'order', None), 'name', '') if sale.order_id else ''
                order_suffix = f", заказ: {order_name}" if order_name else ""
                Income.objects.create(
                    income_type='sales',
                    amount=sale.price,
                    description=f"Продажа готовой продукции: {product_name} x{qty}, клиент: {sale.client.name}{order_suffix}",
                    order_reference=order_reference,
                    date=sale.sold_at.date() if sale.sold_at else timezone.now().date(),
                    created_by=request.user,
                )
        output = self.get_serializer(sale)
        return Response(output.data, status=status.HTTP_201_CREATED)

class FinishedGoodsPageView(TemplateView):
    template_name = 'finished_goods.html'

    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_mobile = any(m in user_agent for m in ['iphone', 'android', 'ipad', 'mobile', 'opera mini', 'blackberry'])
        if is_mobile:
            self.template_name = 'finished_mobile.html'
        else:
            self.template_name = 'finished_goods.html'
        return super().dispatch(request, *args, **kwargs)
