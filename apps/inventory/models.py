from django.db import models


class RawMaterial(models.Model):
    """
    Базовая модель материала на складе.

    Упрощена под текущий UI:
    - поля «Артикул/Код» и «Размер» удалены;
    - добавлено поле страны-производителя.
    """

    name = models.CharField('Название', max_length=100)
    unit = models.CharField('Ед. измерения', max_length=20)
    quantity = models.DecimalField('Количество', max_digits=12, decimal_places=3, default=0)
    min_quantity = models.DecimalField('Мин. остаток', max_digits=12, decimal_places=3, default=0)
    price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2, default=0)
    country = models.CharField('Страна производителя', max_length=100, blank=True)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Сырье/материал'
        verbose_name_plural = 'Сырье и материалы'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_value(self):
        """Общая стоимость материала на складе"""
        return self.quantity * self.price

class MaterialIncoming(models.Model):
    """Модель для истории приходов материалов"""
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='incomings', verbose_name='Материал')
    quantity = models.DecimalField('Количество прихода', max_digits=12, decimal_places=3)
    price_per_unit = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2, null=True, blank=True)
    total_value = models.DecimalField('Общая стоимость', max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField('Примечания', blank=True, null=True)
    created_at = models.DateTimeField('Дата прихода', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Приход материала'
        verbose_name_plural = 'Приходы материалов'
        ordering = ['-created_at']

    def __str__(self):
        return f"Приход {self.material.name} - {self.quantity} {self.material.unit}"

    def save(self, *args, **kwargs):
        # Автоматически рассчитываем общую стоимость
        if self.price_per_unit is not None and not self.total_value:
            self.total_value = self.quantity * self.price_per_unit
        super().save(*args, **kwargs) 

class MaterialConsumption(models.Model):
    """Учет расхода сырья при выполнении задач"""
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, related_name='consumptions')
    quantity = models.DecimalField('Количество израсходовано', max_digits=12, decimal_places=3)
    employee_task = models.ForeignKey('employee_tasks.EmployeeTask', on_delete=models.CASCADE, related_name='material_consumptions')
    workshop = models.ForeignKey('operations_workshops.Workshop', on_delete=models.CASCADE, related_name='inventory_consumptions')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE)
    consumed_at = models.DateTimeField('Дата расхода', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Расход сырья'
        verbose_name_plural = 'Расходы сырья'
        ordering = ['-consumed_at']
    
    def __str__(self):
        return f"{self.material.name} - {self.quantity} ({self.workshop.name})" 