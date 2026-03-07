from django.test import TestCase
from decimal import Decimal

from apps.inventory.models import RawMaterial
from apps.operations.workshops.models import Workshop
from apps.services.models import Service, ServiceMaterial

from .models import CostingSettings, Product, ProductMaterialNorm
from .costing import calculate_product_cost

class ProductCostingTests(TestCase):
    def test_calculate_product_cost_materials_labor_overhead(self):
        # Материалы
        m1 = RawMaterial.objects.create(name="МДФ", unit="лист", quantity=0, price=Decimal("100.00"))
        m2 = RawMaterial.objects.create(name="Клей", unit="кг", quantity=0, price=Decimal("50.00"))

        # Цех
        w1 = Workshop.objects.create(name="Распил")

        # Услуга (труд) + нормы материалов по услуге
        s1 = Service.objects.create(name="Распил", workshop=w1, service_price=Decimal("30.00"), defect_penalty=Decimal("0"))
        ServiceMaterial.objects.create(service=s1, material=m1, amount=Decimal("2.000"))  # 2 листа

        # Продукт
        p = Product.objects.create(name="Дверь", type="door", price=Decimal("1000.00"))
        p.services.add(s1)

        # Доп. норма материала (не из услуги)
        ProductMaterialNorm.objects.create(product=p, workshop=w1, material=m2, amount=Decimal("1.500"))  # 1.5 кг

        # Накладные
        settings = CostingSettings.get_solo()
        settings.overhead_percent = Decimal("10.00")  # 10% от (материалы + труд)
        settings.overhead_per_unit = Decimal("5.00")  # +5 сом/ед
        settings.allocate_overhead_from_finance = False
        settings.save()

        bd = calculate_product_cost(p, quantity=1)

        # Материалы: (2 * 100) + (1.5 * 50) = 200 + 75 = 275
        self.assertEqual(bd["totals"]["materials"], Decimal("275.00"))
        # Труд: 30
        self.assertEqual(bd["totals"]["labor"], Decimal("30.00"))
        # База: 305; накладные: 10%*305=30.5 + 5 = 35.5
        self.assertEqual(bd["totals"]["overhead"], Decimal("35.50"))
        # Итого: 340.5
        self.assertEqual(bd["totals"]["total"], Decimal("340.50"))

        bd2 = calculate_product_cost(p, quantity=3)
        self.assertEqual(bd2["totals_for_quantity"]["total"], Decimal("1021.50"))
