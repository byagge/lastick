from django.db import models

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


class FinishedGoodSale(models.Model):
    finished_good = models.ForeignKey(
        FinishedGood,
        on_delete=models.CASCADE,
        related_name='sales'
    )
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
        return f"Sale #{self.id} - {self.finished_good} -> {self.client}"

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
