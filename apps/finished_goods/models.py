from django.db import models
from django.db.models import Q
from decimal import Decimal, ROUND_HALF_UP

# Create your models here.

class FinishedGood(models.Model):
    STATUS_CHOICES = [
        ('stock', 'На складе'),
        ('issued', 'Выдано'),
        ('reserved', 'Зарезервировано'),
    ]
    
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='finished_goods', verbose_name='Продукт')
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='finished_goods', verbose_name='Позиция заказа')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='finished_goods', verbose_name='Заказ')
    quantity = models.PositiveIntegerField('Количество', default=1)
    received_at = models.DateTimeField('Дата поступления', auto_now_add=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='stock')
    issued_at = models.DateTimeField('Дата выдачи', null=True, blank=True)
    recipient = models.CharField('Получатель', max_length=255, blank=True)
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    
    # Дополнительные поля для отслеживания
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Цех производства')
    packaging_date = models.DateTimeField('Дата упаковки', null=True, blank=True)
    quality_check_passed = models.BooleanField('Проверка качества пройдена', default=False)
    
    class Meta:
        verbose_name = 'Готовая продукция'
        verbose_name_plural = 'Готовая продукция (склад)'
        ordering = ['-received_at']

    def __str__(self):
        item_info = f" — {self.order_item}" if self.order_item else ""
        return f"{self.product} x{self.quantity}{item_info} ({self.get_status_display()})"
    
    def get_order_info(self):
        """Возвращает информацию о заказе"""
        if self.order_item:
            return {
                'order_id': self.order_item.order.id,
                'order_name': self.order_item.order.name,
                'client': self.order_item.order.client.name if self.order_item.order.client else '',
                'size': self.order_item.size,
                'color': self.order_item.color,
                'glass_type': self.order_item.get_glass_type_display(),
                'paint_type': self.order_item.paint_type,
                'paint_color': self.order_item.paint_color,
            }
        return {}
    
    def mark_as_packaged(self, workshop):
        """Отмечает товар как упакованный"""
        from django.utils import timezone
        self.workshop = workshop
        self.packaging_date = timezone.now()
        self.save()
    
    def issue_goods(self, recipient, comment=''):
        """Выдает товар со склада"""
        from django.utils import timezone
        self.status = 'issued'
        self.issued_at = timezone.now()
        self.recipient = recipient
        self.comment = comment
        self.save()
    
    def calculate_actual_cost(self, save=True):
        """
        Рассчитывает и сохраняет фактическую себестоимость на основе реальных затрат:
        - Труд: сумма заработка сотрудников из EmployeeTask по ВСЕМ этапам заказа
        - Сырье: сумма стоимости израсходованного сырья из MaterialConsumption по ВСЕМ этапам заказа
        
        Система собирает затраты по ВСЕМ этапам заказа, даже если они не напрямую связаны с order_item.
        Это позволяет учитывать затраты в реальном времени на каждом этапе производства.
        
        Если save=True, сохраняет результаты в базу данных.
        """
        from apps.employee_tasks.models import EmployeeTask
        from apps.inventory.models import MaterialConsumption
        from apps.orders.models import OrderStage
        from django.db import transaction
        
        # Получаем связанный заказ
        order = self.order
        
        if not order:
            return None
        
        # Собираем ВСЕ этапы заказа (независимо от order_item)
        # Это позволяет учитывать затраты на всех этапах производства
        all_stages = OrderStage.objects.filter(order=order)
        stage_ids = list(all_stages.values_list('id', flat=True))
        
        if not stage_ids:
            # Если нет этапов, пытаемся найти затраты напрямую по заказу
            employee_tasks = EmployeeTask.objects.filter(stage__order=order)
            material_consumptions = MaterialConsumption.objects.filter(order=order)
        else:
            # Собираем все задачи сотрудников по ВСЕМ этапам заказа
            employee_tasks = EmployeeTask.objects.filter(stage_id__in=stage_ids)
            
            # Собираем все расходы сырья по ВСЕМ этапам заказа
            material_consumptions = MaterialConsumption.objects.filter(
                order=order
            ).filter(
                Q(employee_task__stage_id__in=stage_ids) | Q(employee_task__isnull=True)
            )
        
        # Суммируем заработок сотрудников (net_earnings - чистый заработок после штрафов)
        total_labor_cost = Decimal('0')
        labor_tasks = []
        
        for task in employee_tasks:
            if task.net_earnings and task.net_earnings > 0:
                labor_cost = Decimal(str(task.net_earnings))
                total_labor_cost += labor_cost
                
                labor_tasks.append({
                    'task': task,
                    'cost': labor_cost,
                })
        
        # Суммируем стоимость израсходованного сырья
        total_material_cost = Decimal('0')
        material_consumptions_list = []
        
        for consumption in material_consumptions:
            # Используем цену закупки, если есть, иначе цену продажи
            material_price = consumption.material.purchase_price or consumption.material.price or Decimal('0')
            material_cost = Decimal(str(consumption.quantity)) * Decimal(str(material_price))
            total_material_cost += material_cost
            
            material_consumptions_list.append({
                'consumption': consumption,
                'cost': material_cost,
            })
        
        # Если по заказу вообще нет ни задач, ни расходов сырья —
        # возвращаем None, чтобы фронт мог использовать нормативную себестоимость
        if total_labor_cost == 0 and total_material_cost == 0:
            return None

        # Общая себестоимость
        total_cost = total_labor_cost + total_material_cost
        
        # Себестоимость на единицу товара
        quantity = Decimal(str(self.quantity or 1))
        if quantity > 0:
            cost_per_unit = (total_cost / quantity).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            cost_per_unit = Decimal('0')
        
        result = {
            'cost_per_unit': cost_per_unit,
            'total_cost': total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'labor_cost': total_labor_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'material_cost': total_material_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        }
        
        # Сохраняем в базу данных, если требуется
        if save:
            with transaction.atomic():
                # Создаем или обновляем себестоимость
                costing, created = FinishedGoodCosting.objects.update_or_create(
                    finished_good=self,
                    defaults={
                        'cost_per_unit': result['cost_per_unit'],
                        'total_cost': result['total_cost'],
                        'labor_cost': result['labor_cost'],
                        'material_cost': result['material_cost'],
                    }
                )
                
                # Удаляем старые детализации
                costing.labor_costs.all().delete()
                costing.material_costs.all().delete()
                
                # Создаем детализацию по труду
                for item in labor_tasks:
                    FinishedGoodLaborCost.objects.create(
                        costing=costing,
                        employee_task=item['task'],
                        cost=item['cost'],
                        completed_quantity=item['task'].completed_quantity,
                    )
                
                # Создаем детализацию по сырью
                for item in material_consumptions_list:
                    FinishedGoodMaterialCost.objects.create(
                        costing=costing,
                        material_consumption=item['consumption'],
                        cost=item['cost'],
                        quantity=item['consumption'].quantity,
                    )
        
        return result


class FinishedGoodCosting(models.Model):
    """
    Фактическая себестоимость готовой продукции.
    Рассчитывается на основе реальных затрат на труд и сырье.
    """
    finished_good = models.OneToOneField(
        FinishedGood,
        on_delete=models.CASCADE,
        related_name='costing',
        verbose_name='Готовая продукция'
    )
    
    # Себестоимость на единицу товара
    cost_per_unit = models.DecimalField(
        'Себестоимость за единицу',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Общая себестоимость всей партии
    total_cost = models.DecimalField(
        'Общая себестоимость',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Затраты на труд
    labor_cost = models.DecimalField(
        'Затраты на труд',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Затраты на сырье
    material_cost = models.DecimalField(
        'Затраты на сырье',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Дата расчета
    calculated_at = models.DateTimeField('Дата расчета', auto_now=True)
    
    class Meta:
        verbose_name = 'Себестоимость готовой продукции'
        verbose_name_plural = 'Себестоимость готовой продукции'
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"Себестоимость {self.finished_good}: {self.cost_per_unit} за единицу"


class FinishedGoodLaborCost(models.Model):
    """
    Детализация затрат на труд для готовой продукции.
    Связывает FinishedGoodCosting с EmployeeTask.
    """
    costing = models.ForeignKey(
        FinishedGoodCosting,
        on_delete=models.CASCADE,
        related_name='labor_costs',
        verbose_name='Себестоимость'
    )
    
    employee_task = models.ForeignKey(
        'employee_tasks.EmployeeTask',
        on_delete=models.CASCADE,
        related_name='finished_good_labor_costs',
        verbose_name='Задача сотрудника'
    )
    
    # Затраты на труд от этой задачи
    cost = models.DecimalField(
        'Затраты',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Количество выполненной работы
    completed_quantity = models.PositiveIntegerField('Выполнено', default=0)
    
    class Meta:
        verbose_name = 'Затраты на труд'
        verbose_name_plural = 'Затраты на труд'
        unique_together = ('costing', 'employee_task')
    
    def __str__(self):
        employee_name = self.employee_task.employee.get_full_name() if self.employee_task.employee else 'Неизвестно'
        return f"Труд: {employee_name} - {self.cost}"


class FinishedGoodMaterialCost(models.Model):
    """
    Детализация затрат на сырье для готовой продукции.
    Связывает FinishedGoodCosting с MaterialConsumption.
    """
    costing = models.ForeignKey(
        FinishedGoodCosting,
        on_delete=models.CASCADE,
        related_name='material_costs',
        verbose_name='Себестоимость'
    )
    
    material_consumption = models.ForeignKey(
        'factory_inventory.MaterialConsumption',
        on_delete=models.CASCADE,
        related_name='finished_good_material_costs',
        verbose_name='Расход сырья'
    )
    
    # Затраты на сырье от этого расхода
    cost = models.DecimalField(
        'Затраты',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Количество израсходованного сырья
    quantity = models.DecimalField(
        'Количество',
        max_digits=12,
        decimal_places=3,
        default=Decimal('0.000')
    )
    
    class Meta:
        verbose_name = 'Затраты на сырье'
        verbose_name_plural = 'Затраты на сырье'
        unique_together = ('costing', 'material_consumption')
    
    def __str__(self):
        material_name = self.material_consumption.material.name if self.material_consumption.material else 'Неизвестно'
        return f"Сырье: {material_name} - {self.cost}"


class FinishedGoodSale(models.Model):
    finished_good = models.ForeignKey(
        FinishedGood,
        on_delete=models.CASCADE,
        related_name='sales'
    )
    quantity = models.PositiveIntegerField(default=1)
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.PROTECT,
        related_name='finished_good_sales'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finished_good_sales'
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    sold_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sold_at']

    def __str__(self):
        return f"Sale #{self.id} - {self.finished_good} x{self.quantity} -> {self.client}"
    
    def get_profit(self):
        """Рассчитывает прибыль от продажи на основе фактической себестоимости"""
        if not self.finished_good.costing:
            return None
        
        cost_per_unit = self.finished_good.costing.cost_per_unit
        unit_price = Decimal(str(self.price)) / Decimal(str(self.quantity))
        profit_per_unit = unit_price - cost_per_unit
        total_profit = profit_per_unit * Decimal(str(self.quantity))
        
        return {
            'unit_price': unit_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'cost_per_unit': cost_per_unit,
            'profit_per_unit': profit_per_unit.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_profit': total_profit.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        }

def create_example_finished_good():
    from apps.products.models import Product
    from apps.orders.models import Order
    product = Product.objects.first()
    order = Order.objects.first()
    if not product:
        print('Нет продуктов для примера!')
        return
    fg = FinishedGood.objects.create(
        product=product,
        quantity=10,
        order=order,
        status='stock',
        recipient='Иванов Иван',
        comment='Тестовая партия готовой продукции'
    )
    print('Пример готовой продукции создан:', fg)


# Сигналы для автоматического расчета себестоимости
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender=FinishedGood)
def calculate_finished_good_cost(sender, instance, created, **kwargs):
    """
    Автоматически рассчитывает себестоимость при создании или обновлении FinishedGood.
    Рассчитывается для всех товаров на складе (status='stock') и в процессе готовки.
    """
    # Рассчитываем себестоимость только если есть связанный заказ
    # Можно рассчитывать даже если товар еще не готов (в процессе производства)
    if instance.order:
        try:
            # Используем update_fields для оптимизации - пересчитываем только если изменились важные поля
            update_fields = kwargs.get('update_fields')
            if update_fields is None or any(field in update_fields for field in ['order', 'order_item', 'quantity', 'status']):
                instance.calculate_actual_cost(save=True)
        except Exception as e:
            # Логируем ошибку, но не прерываем сохранение
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Ошибка расчета себестоимости для FinishedGood #{instance.id}: {e}")


@receiver(post_save, sender='employee_tasks.EmployeeTask')
@receiver(post_save, sender='factory_inventory.MaterialConsumption')
def recalculate_finished_good_cost(sender, instance, **kwargs):
    """
    Пересчитывает себестоимость готовой продукции в реальном времени при изменении задач или расхода сырья.
    Система автоматически обновляет себестоимость для всех готовой продукции, связанной с заказом.
    """
    from apps.finished_goods.models import FinishedGood
    from django.db import transaction
    
    # Определяем связанный заказ
    order = None
    if hasattr(instance, 'stage'):
        order = instance.stage.order if instance.stage else None
    elif hasattr(instance, 'order'):
        order = instance.order
    
    if order:
        # Пересчитываем себестоимость для всех готовой продукции этого заказа
        # Используем select_for_update для предотвращения race conditions
        finished_goods = FinishedGood.objects.filter(order=order).select_related('order', 'order_item')
        
        for fg in finished_goods:
            try:
                with transaction.atomic():
                    fg.calculate_actual_cost(save=True)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Ошибка пересчета себестоимости для FinishedGood #{fg.id}: {e}", exc_info=True)
