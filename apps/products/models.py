from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.inventory.models import RawMaterial
from apps.operations.workshops.models import Workshop
from apps.services.models import Service

# Create your models here.

class Product(models.Model):
    PRODUCT_TYPES = [
        ("door", "Дверь"),
        # Можно добавить другие типы позже
    ]
    
    GLASS_TYPES = [
        ("sandblasted", "Пескоструйный"),
        ("uv", "УФ"),
    ]
    
    name = models.CharField('Наименование', max_length=255)
    type = models.CharField('Тип', max_length=50, choices=PRODUCT_TYPES, default="door")
    description = models.TextField('Описание', blank=True)
    is_glass = models.BooleanField('Стеклянный', default=False)
    glass_type = models.CharField(
        'Тип стекла', 
        max_length=20, 
        choices=GLASS_TYPES, 
        null=True, 
        blank=True,
        help_text='Указывается только для стеклянных изделий'
    )
    img = models.ImageField('Изображение', upload_to='products/', blank=True, null=True)
    services = models.ManyToManyField(Service, related_name="products", verbose_name="Услуги для продукта")
    price = models.DecimalField('Цена за продукт', max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return self.name

    def get_materials_with_amounts(self):
        """
        Возвращает словарь {материал: общее_количество} по всем выбранным услугам.
        Количество — Decimal (сумма норм расхода).
        """
        from collections import defaultdict
        materials = defaultdict(Decimal)
        for service in self.services.all():
            for sm in service.service_materials.all():
                materials[sm.material] += (sm.amount or Decimal('0'))
        return dict(materials)

    def get_cost_price(self):
        """
        Себестоимость (нормативная): материалы + труд (сдельная оплата услуг) + накладные.
        """
        from .costing import calculate_product_cost

        breakdown = calculate_product_cost(self, quantity=1)
        return breakdown["totals"]["total"]

    def get_cost_breakdown(self, quantity=1):
        """
        Возвращает структуру с детализацией себестоимости.
        """
        from .costing import calculate_product_cost

        return calculate_product_cost(self, quantity=quantity)

class ProductMaterialNorm(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='Продукт')
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, verbose_name='Цех')
    material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE, verbose_name='Сырьё')
    amount = models.DecimalField('Расход на единицу продукции', max_digits=12, decimal_places=3, default=Decimal('0'))

    class Meta:
        verbose_name = 'Норма расхода сырья'
        verbose_name_plural = 'Нормы расхода сырья'
        unique_together = ('product', 'workshop', 'material')

    def __str__(self):
        return f'{self.product} - {self.workshop}: {self.material} ({self.amount})'


class CostingSettings(models.Model):
    """
    Настройки расчёта себестоимости (singleton).

    - Накладные можно задавать как процент от (материалы + труд)
    - и/или как фиксированную сумму на единицу.
    - При желании можно дополнительно включить распределение накладных из finance по категориям.
    """

    overhead_percent = models.DecimalField(
        'Накладные, %',
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Процент накладных от суммы (материалы + труд). Например 10.00 = 10%'
    )
    overhead_per_unit = models.DecimalField(
        'Накладные на единицу (сом)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Фиксированные накладные расходы на 1 единицу продукции'
    )

    allocate_overhead_from_finance = models.BooleanField(
        'Распределять накладные из Finance',
        default=False,
        help_text='Если включено, накладные дополнительно считаются как (сумма расходов по выбранным категориям) / (выпуск за период)'
    )
    overhead_period_days = models.PositiveIntegerField(
        'Период распределения (дней)',
        default=30,
        help_text='За сколько дней брать расходы и выпуск для распределения накладных'
    )
    overhead_categories = models.ManyToManyField(
        'finance.ExpenseCategory',
        blank=True,
        related_name='costing_settings',
        verbose_name='Категории накладных',
        help_text='Категории расходов, которые считаются накладными (аренда, свет, транспорт и т.д.)'
    )

    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Настройки себестоимости'
        verbose_name_plural = 'Настройки себестоимости'

    def __str__(self):
        return "Настройки себестоимости"

    def save(self, *args, **kwargs):
        # singleton
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={
            "overhead_percent": Decimal('0.00'),
            "overhead_per_unit": Decimal('0.00'),
            "allocate_overhead_from_finance": False,
            "overhead_period_days": 30,
        })
        return obj
