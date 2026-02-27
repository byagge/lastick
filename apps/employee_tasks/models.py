from django.db import models
from apps.orders.models import OrderStage
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
import logging

User = get_user_model()

class EmployeeTask(models.Model):
    stage = models.ForeignKey(OrderStage, on_delete=models.CASCADE, related_name='employee_tasks')
    employee = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    completed_quantity = models.PositiveIntegerField(default=0)
    defective_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Новые поля для заработка и штрафов
    earnings = models.DecimalField('Заработок', max_digits=10, decimal_places=2, default=0)
    penalties = models.DecimalField('Штрафы', max_digits=10, decimal_places=2, default=0)
    net_earnings = models.DecimalField('Чистый заработок', max_digits=10, decimal_places=2, default=0)
    
    # Пользовательская цена за единицу для данного назначения (перекрывает цену услуги)
    custom_unit_price = models.DecimalField('Индивидуальная цена за единицу', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Количество слоёв на единицу (актуально для цеха ID=7)
    layers_per_unit = models.PositiveIntegerField('Слоёв на единицу', default=1)

    # Дополнительные штрафы (вручную начисленные, например при подтверждении брака)
    additional_penalties = models.DecimalField('Дополнительные штрафы', max_digits=10, decimal_places=2, default=0)
    
    # Связь с услугой через цех
    @property
    def service(self):
        """Получаем услугу через цех этапа и название операции"""
        if self.stage and self.stage.workshop:
            from apps.services.models import Service
            try:
                # Если есть название операции, ищем по нему
                if self.stage.operation and self.stage.operation.strip():
                    service = Service.objects.filter(
                        workshop=self.stage.workshop, 
                        name=self.stage.operation,
                        is_active=True
                    ).first()
                    
                    if service:
                        return service
                
                # Если по операции не найдено или операция пустая, ищем первую активную услугу для цеха
                service = Service.objects.filter(
                    workshop=self.stage.workshop, 
                    is_active=True
                ).first()
                
                return service
            except Exception:
                return None
        return None
    class Meta:
        verbose_name = 'Задача сотрудника'
        verbose_name_plural = 'Задачи сотрудников'

    def __str__(self):
        return f"Задача {self.employee} - {self.stage}"

    def calculate_earnings(self):
        """Рассчитывает заработок, штрафы и чистый заработок"""
        from decimal import Decimal, InvalidOperation
        
        print(f"\n=== DEBUG: Расчет заработка для EmployeeTask #{self.id} ===")
        print(f"Сотрудник: {self.employee}")
        print(f"Этап: {self.stage}")
        print(f"Цех: {getattr(self.stage, 'workshop', 'N/A')}")
        print(f"Операция: {getattr(self.stage, 'operation', 'N/A')}")
        print(f"Выполнено: {self.completed_quantity}, Брак: {self.defective_quantity}")
        print(f"Индивидуальная цена: {self.custom_unit_price}")
        print(f"Слои на единицу: {self.layers_per_unit}")
        
        # Базовая ставка за единицу работы (если услуга не найдена)
        BASE_RATE = Decimal('100.00')  # 100 рублей за единицу
        BASE_PENALTY_RATE = Decimal('50.00')  # 50 рублей за единицу брака
        
        # Определяем ставку за единицу: приоритет custom_unit_price → цена продукта → цена услуги → базовая
        service_price = None
        penalty_rate = None
        price_source = 'unknown'
        real_cost_sum = None  # Сумма реальной стоимости по продуктам для агрегированных этапов
        real_cost_qty = 0     # Реальное выполненное количество, учтенное в сумме
        
        # 1) Индивидуальная цена от мастера
        if self.custom_unit_price is not None:
            try:
                service_price = Decimal(str(self.custom_unit_price))
                price_source = 'custom_unit_price'
                print(f"✓ Используется индивидуальная цена: {service_price}")
            except InvalidOperation:
                service_price = None
                print("✗ Ошибка в индивидуальной цене")
            penalty_rate = self.service.defect_penalty if self.service else BASE_PENALTY_RATE
        else:
            print("Индивидуальная цена не задана, ищем услугу...")
            
            # 2) Цена услуги ДЛЯ КОНКРЕТНОГО ТОВАРА в данном цехе (приоритетная логика)
            matched_service = None
            try:
                order_item = getattr(self.stage, 'order_item', None)
                product = getattr(order_item, 'product', None) if order_item else None
                workshop = getattr(self.stage, 'workshop', None)
                operation = getattr(self.stage, 'operation', None)
                
                print(f"Поиск услуги для товара: {product}")
                print(f"Цех: {workshop}")
                print(f"Операция: '{operation}'")
                
                # Если этап агрегированный (order_item отсутствует) — покажем товары заявки
                if (product is None) and getattr(self.stage, 'order', None) and hasattr(self.stage.order, 'items'):
                    try:
                        items_info = ", ".join([f"{it.product.name if it.product else '—'} x{it.quantity}" for it in self.stage.order.items.all()])
                        print(f"Товары в заявке: {items_info}")
                    except Exception:
                        pass
                
                if product and workshop:
                    # Пытаемся найти услугу по продукту, цеху и названию операции
                    qs = product.services.filter(workshop=workshop)
                    print(f"Найдено услуг для товара в цехе: {qs.count()}")
                    
                    # Всегда берем первую активную услугу для продукта в цехе (не ищем по названию операции)
                    matched_service = qs.filter(is_active=True).first()
                    if matched_service:
                        print(f"✓ Берем первую активную услугу: {matched_service.name}")
                    else:
                        # Если активных услуг нет, берем любую
                        matched_service = qs.first()
                        if matched_service:
                            print(f"  Активных услуг нет, берем любую: {matched_service.name}")
                        
                    if matched_service:
                        service_price = matched_service.service_price
                        penalty_rate = matched_service.defect_penalty
                        price_source = f'product.services[{matched_service.id}]@{workshop.id}'
                        print(f"✓ Найдена услуга товара: {matched_service.name} = {service_price}")
                    else:
                        print(f"✗ Услуга для товара {product.name} в цехе {workshop} не найдена!")
            except Exception as e:
                matched_service = None
                print(f"✗ Ошибка поиска услуги товара: {e}")            
                        # 2b) Агрегированный этап: считаем реальную стоимость по каждому продукту отдельно
            if service_price is None:
                print("Услуга товара не найдена, считаем реальную стоимость по продуктам...")
                try:
                    order = getattr(self.stage, 'order', None)
                    workshop = getattr(self.stage, 'workshop', None)
                    operation = getattr(self.stage, 'operation', None)
                    if order and workshop and hasattr(order, 'items') and order.items.exists():
                        print(f"Позиции заказа: {order.items.count()}")
                        
                        # Считаем реальную стоимость для выполненного количества
                        real_total_value = Decimal('0')
                        real_total_qty = 0
                        remaining_completed = self.completed_quantity
                        
                        for it in order.items.all():
                            it_qty = int(getattr(it, 'quantity', 0) or 0)
                            it_service = None
                            it_price = Decimal('0')
                            
                            try:
                                if it.product:
                                    # Ищем услугу для конкретного продукта в данном цехе
                                    qs = it.product.services.filter(workshop=workshop)
                                    print(f"Товар {it.product.name}: найдено услуг в цехе {workshop}: {qs.count()}")
                                    
                                    # Всегда берем первую активную услугу для продукта в цехе (не ищем по названию операции)
                                    it_service = qs.filter(is_active=True).first()
                                    if it_service:
                                        print(f"  Берем первую активную услугу: {it_service.name}")
                                    else:
                                        # Если активных услуг нет, берем любую
                                        it_service = qs.first()
                                        if it_service:
                                            print(f"  Активных услуг нет, берем любую: {it_service.name}")
                                    
                                    if it_service:
                                        it_price = Decimal(str(it_service.service_price or 0))
                                        print(f"  Цена услуги '{it_service.name}': {it_price}")
                                    else:
                                        print(f"  Услуга для товара {it.product.name} в цехе {workshop} не найдена!")
                                        
                            except Exception as e:
                                print(f"✗ Ошибка поиска услуги для {it.product}: {e}")
                                it_service = None
                                it_price = Decimal('0')
                            
                            # Считаем реальную стоимость для этого продукта
                            # Берем количество из позиции или оставшееся выполненное количество
                            executed_qty = min(remaining_completed, it_qty)
                            if executed_qty > 0:
                                real_total_value += (it_price * Decimal(str(executed_qty)))
                                real_total_qty += executed_qty
                                remaining_completed -= executed_qty
                                print(f"  Выполнено {executed_qty} x {it_price} = {it_price * Decimal(str(executed_qty))}")
                            
                            # Если все выполнено - выходим из цикла
                            if remaining_completed <= 0:
                                break
                        
                        if real_total_qty > 0:
                            # Сохраняем точную сумму и количество для дальнейшего расчета заработка без усреднения
                            real_cost_sum = real_total_value
                            real_cost_qty = real_total_qty
                            price_source = 'real_cost_by_products_sum'
                            print(f"✓ Реальная стоимость (сумма): {real_cost_sum} за {real_cost_qty} выполненных единиц")
                        else:
                            print("✗ Не выполнено ни одной единицы, не можем рассчитать стоимость")
                except Exception as e:
                    print(f"✗ Ошибка расчета реальной стоимости: {e}")
                    pass
            
            # 3) Цена услуги этапа (если не удалось выше) и штраф
            if service_price is None:
                print("Взвешенная цена не рассчитана, ищем услугу цеха...")
                if self.service:
                    service_price = self.service.service_price
                    price_source = 'service.service_price'
                    penalty_rate = self.service.defect_penalty
                    print(f"✓ Найдена услуга цеха: {self.service.name} = {service_price}")
                else:
                    service_price = BASE_RATE
                    price_source = 'BASE_RATE'
                    print(f"✓ Используется базовая ставка: {BASE_RATE}")            
            # Если штраф не определен выше, используем базовый
            if penalty_rate is None:
                if self.service:
                    penalty_rate = self.service.defect_penalty
                    print(f"Штраф за брак из услуги цеха: {penalty_rate}")
                else:
                    penalty_rate = BASE_PENALTY_RATE
                    print(f"Штраф за брак базовый: {penalty_rate}")        
        # Множитель слоёв только для цеха ID=7
        try:
            workshop_id = getattr(self.stage.workshop, 'id', None)
        except Exception:
            workshop_id = None
        layers_multiplier = self.layers_per_unit if (workshop_id == 7 and int(self.layers_per_unit or 1) > 0) else 1
        print(f"Множитель слоев (цех {workshop_id}): {layers_multiplier}")
        
        # Заработок за выполненную работу
        if real_cost_sum is not None and real_cost_qty > 0:
            # Агрегированный этап: используем точную сумму по продуктам, без усреднения
            gross = Decimal(str(real_cost_sum)) * Decimal(str(layers_multiplier))
            self.earnings = gross.quantize(Decimal('0.1'))
            print(f"Заработок (точная сумма по продуктам): {real_cost_sum} x {layers_multiplier} = {self.earnings}")
        else:
            # Обычный этап или когда удалось определить единичную цену
            gross = (Decimal(str(self.completed_quantity)) * Decimal(str(service_price))) * Decimal(str(layers_multiplier))
            self.earnings = gross.quantize(Decimal('0.1'))
            print(f"Заработок: {self.completed_quantity} x {service_price} x {layers_multiplier} = {self.earnings}")
        
        # Штрафы: за брак + дополнительные вручную начисленные
        base_defect_penalties = Decimal(str(self.defective_quantity)) * Decimal(str(penalty_rate))
        manual_penalties = Decimal(str(self.additional_penalties or 0))
        raw_penalties = base_defect_penalties + manual_penalties
        self.penalties = raw_penalties.quantize(Decimal('0.1'))
        print(f"Штрафы: брак {self.defective_quantity} x {penalty_rate} = {base_defect_penalties} + ручные {manual_penalties} = {self.penalties}")
        
        # Чистый заработок
        raw_net = self.earnings - self.penalties
        self.net_earnings = raw_net.quantize(Decimal('0.1'))
        print(f"Чистый заработок: {self.earnings} - {self.penalties} = {self.net_earnings}")
        print(f"Источник цены: {price_source}")
        print("=== КОНЕЦ DEBUG ===\n")

    @property
    def is_completed(self):
        """Проверяет, выполнена ли задача полностью"""
        return self.completed_quantity >= self.quantity
    
    @property
    def title(self):
        """Возвращает название задачи на основе этапа"""
        if self.stage:
            return f"{self.stage.operation} - {self.stage.order.name if self.stage.order else 'Заказ'}"
        return f"Задача #{self.id}"
    
    @property
    def plan_quantity(self):
        """Возвращает план задачи (для совместимости с фронтендом)"""
        return self.quantity
    
    @property
    def started_at(self):
        """Возвращает дату начала задачи"""
        return self.created_at

    def consume_materials(self, delta_completed_quantity: int):
        """Учитывает расход сырья при выполнении работы для приращения delta_completed_quantity"""
        if not self.service or not delta_completed_quantity:
            return
        
        from apps.services.models import ServiceMaterial
        
        # Получаем все материалы для данной услуги
        service_materials = ServiceMaterial.objects.filter(service=self.service)
        
        for service_material in service_materials:
            material = service_material.material
            # Рассчитываем количество израсходованного сырья ТОЛЬКО для дельты
            consumed_amount = service_material.amount * Decimal(str(delta_completed_quantity))
            
            # Обновляем количество на складе
            if material.quantity >= consumed_amount:
                material.quantity -= consumed_amount
                material.save()
                
                # Логируем расход
                try:
                    from apps.inventory.models import MaterialConsumption
                    MaterialConsumption.objects.create(
                        material=material,
                        quantity=consumed_amount,
                        employee_task=self,
                        workshop=self.stage.workshop,
                        order=self.stage.order
                    )
                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение
                    logging.getLogger(__name__).warning(f"Ошибка создания записи расхода: {e}")
            else:
                # Если недостаточно сырья, создаем предупреждение
                try:
                    from apps.notifications.models import Notification
                    Notification.objects.create(
                        user=self.employee,
                        title="Недостаточно сырья",
                        message=f"Недостаточно материала {material.name} для выполнения задачи",
                        notification_type="warning"
                    )
                except Exception as e:
                    # Логируем ошибку, но не прерываем выполнение
                    logging.getLogger(__name__).warning(f"Ошибка создания уведомления: {e}")

@receiver(pre_save, sender=EmployeeTask)
def create_defect_on_defective_change(sender, instance, **kwargs):
    """Создает записи браков в новой системе при изменении defective_quantity и сохраняет предыдущее значение net_earnings"""
    if instance.pk:
        try:
            old_instance = EmployeeTask.objects.get(pk=instance.pk)
            # Дельта выполненного для последующего списания материалов
            delta_completed = int(instance.completed_quantity) - int(old_instance.completed_quantity)
            instance._delta_completed_quantity = max(delta_completed, 0)
            # Сохраняем старое значение чистого заработка для корректного обновления баланса
            instance._old_net_earnings = Decimal(str(old_instance.net_earnings or 0))

            # Создание браков в новой системе
            if instance.defective_quantity > old_instance.defective_quantity:
                from apps.defects.models import Defect
                defect_quantity = instance.defective_quantity - old_instance.defective_quantity
                
                # Создаем записи браков для каждого единицы брака
                if defect_quantity > 0:
                    Defect.objects.create(
                        employee_task=instance,
                        product=(
                            instance.stage.order_item.product
                            if instance.stage.order_item
                            else (
                                instance.stage.order.product
                                if getattr(instance.stage, 'order', None)
                                and getattr(instance.stage.order, 'product', None)
                                else None
                            )
                        ),
                        user=instance.employee,
                        quantity=Decimal(str(defect_quantity)),
                    )
        except EmployeeTask.DoesNotExist:
            instance._delta_completed_quantity = 0
            instance._old_net_earnings = Decimal('0')
    else:
        instance._delta_completed_quantity = 0
        instance._old_net_earnings = Decimal('0')

@receiver(post_save, sender=EmployeeTask)
def update_earnings_and_materials(sender, instance, created, **kwargs):
    """Обновляет заработок, учитывает расход сырья и пополняет баланс пользователя"""
    try:
        with transaction.atomic():
            # Рассчитываем заработок по текущим значениям
            instance.calculate_earnings()
            # Списываем материалы по дельте; если запись только что создана и есть выполненное количество, спишем сразу
            delta = getattr(instance, '_delta_completed_quantity', None)
            if delta is None:
                delta = instance.completed_quantity if created else 0
            if int(delta) > 0:
                instance.consume_materials(int(delta))
            # Обновляем агрегаты в базе без рекурсии
            EmployeeTask.objects.filter(pk=instance.pk).update(
                earnings=instance.earnings,
                penalties=instance.penalties,
                net_earnings=instance.net_earnings
            )
            # Пополняем баланс сотрудника разницей чистого заработка
            old_net = getattr(instance, '_old_net_earnings', Decimal('0'))
            new_net = Decimal(str(instance.net_earnings or 0))
            delta_net = new_net - old_net
            if delta_net != 0:
                from django.db.models import F
                User.objects.filter(pk=instance.employee_id).update(balance=F('balance') + delta_net)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        logging.getLogger(__name__).warning(f"Ошибка в update_earnings_and_materials: {e}")
