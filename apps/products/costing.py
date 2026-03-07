from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional

from django.db.models import Sum
from django.utils import timezone

from .models import CostingSettings, ProductMaterialNorm


MONEY_Q = Decimal('0.01')


def qmoney(value: Decimal) -> Decimal:
    return (value or Decimal('0')).quantize(MONEY_Q, rounding=ROUND_HALF_UP)


def to_decimal(value: Any, default: str = '0') -> Decimal:
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _finance_overhead_per_unit(settings: CostingSettings, as_of: Optional[date]) -> Decimal:
    """
    Рассчитывает накладные (сом/ед) как (расходы по выбранным категориям) / (выпуск за период).
    Возвращает 0, если нет категорий или выпуск == 0.
    """
    if not settings.allocate_overhead_from_finance:
        return Decimal('0')

    categories_qs = settings.overhead_categories.all()
    if not categories_qs.exists():
        return Decimal('0')

    end_date = as_of or timezone.localdate()
    start_date = end_date - timedelta(days=int(settings.overhead_period_days or 30))

    # Импорты внутри, чтобы не держать жёсткую связь на уровне модуля
    from apps.finance.models import Expense
    from apps.finished_goods.models import FinishedGood

    overhead_total = Expense.objects.filter(
        category__in=categories_qs,
        date__gte=start_date,
        date__lte=end_date,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

    produced_qty = FinishedGood.objects.filter(
        received_at__date__gte=start_date,
        received_at__date__lte=end_date,
    ).aggregate(total=Sum('quantity'))['total'] or 0

    produced_qty = int(produced_qty or 0)
    if produced_qty <= 0:
        return Decimal('0')

    return to_decimal(overhead_total) / Decimal(str(produced_qty))


def _actual_labor_per_unit(settings: CostingSettings, as_of: Optional[date]) -> Optional[Decimal]:
    """
    Фактический труд (сом/ед) = (фиксированная зарплата работников + сдельные выплаты) / выпуск за период.

    - Фиксированная часть: берётся из User.fixed_salary, пропорционально количеству дней периода.
    - Сдельная часть: суммируются EmployeeTask.earnings за период.
    - Выпуск: количество FinishedGood за тот же период.
    """
    if not settings.use_actual_labor:
        return None

    end_date = as_of or timezone.localdate()
    period_days = int(settings.labor_period_days or 30)
    if period_days <= 0:
        period_days = 30
    start_date = end_date - timedelta(days=period_days)

    from apps.users.models import User
    from apps.employee_tasks.models import EmployeeTask
    from apps.finished_goods.models import FinishedGood

    # Фиксированная зарплата рабочих (worker)
    fixed_sum = Decimal('0')
    for u in User.objects.filter(role=User.Role.WORKER):
        if u.fixed_salary:
            # Пропорция периода к условному месяцу (30 дней)
            coef = Decimal(str(period_days)) / Decimal('30')
            fixed_sum += to_decimal(u.fixed_salary) * coef

    # Сдельные выплаты по задачам за период
    tasks_qs = EmployeeTask.objects.filter(
        completed_at__date__gte=start_date,
        completed_at__date__lte=end_date,
    )
    piece_sum = tasks_qs.aggregate(total=Sum('earnings'))['total'] or Decimal('0')

    total_labor = to_decimal(fixed_sum) + to_decimal(piece_sum)

    # Выпуск готовой продукции за период
    produced_qty = FinishedGood.objects.filter(
        received_at__date__gte=start_date,
        received_at__date__lte=end_date,
    ).aggregate(total=Sum('quantity'))['total'] or 0
    produced_qty = int(produced_qty or 0)
    if produced_qty <= 0 or total_labor <= 0:
        return None

    return to_decimal(total_labor) / Decimal(str(produced_qty))


def calculate_product_cost(product, quantity: int = 1, as_of: Optional[date] = None) -> Dict[str, Any]:
    """
    Нормативная себестоимость продукта.

    Источники:
    - **Материалы**: ServiceMaterial по выбранным услугам продукта + доп. нормы ProductMaterialNorm
    - **Труд**: сумма Service.service_price по выбранным услугам продукта (сдельная оплата)
    - **Накладные**: из CostingSettings (процент и/или фикс на ед) + (опционально) распределение из finance
    """
    q = max(int(quantity or 1), 1)
    settings = CostingSettings.get_solo()

    # Материалы по услугам
    materials_map: Dict[int, Dict[str, Any]] = {}
    materials_total = Decimal('0')

    # Важно: product.services может быть не префетчен — код должен работать в любом случае
    for service in product.services.all():
        for sm in service.service_materials.select_related('material').all():
            m = sm.material
            if not m:
                continue
            mid = int(m.id)
            amount = to_decimal(sm.amount, default='0')
            if mid not in materials_map:
                materials_map[mid] = {
                    "material_id": mid,
                    "name": m.name,
                    "unit": m.unit,
                    "amount": Decimal('0'),
                    "price": to_decimal(m.price, default='0'),
                    "sources": [],
                }
            materials_map[mid]["amount"] += amount
            materials_map[mid]["sources"].append({"source": "service", "service_id": service.id, "amount": amount})

    # Доп. нормы материалов (если заведены)
    norms = ProductMaterialNorm.objects.filter(product=product).select_related('material', 'workshop')
    for n in norms:
        m = n.material
        if not m:
            continue
        mid = int(m.id)
        amount = to_decimal(n.amount, default='0')
        if mid not in materials_map:
            materials_map[mid] = {
                "material_id": mid,
                "name": m.name,
                "unit": m.unit,
                "amount": Decimal('0'),
                "price": to_decimal(m.price, default='0'),
                "sources": [],
            }
        materials_map[mid]["amount"] += amount
        materials_map[mid]["sources"].append({
            "source": "product_norm",
            "workshop_id": getattr(n.workshop, 'id', None),
            "workshop_name": getattr(n.workshop, 'name', None),
            "amount": amount,
        })

    materials_list = []
    for row in materials_map.values():
        cost = to_decimal(row["price"]) * to_decimal(row["amount"])
        row["cost"] = qmoney(cost)
        row["amount"] = to_decimal(row["amount"])
        row["price"] = qmoney(to_decimal(row["price"]))
        materials_total += to_decimal(row["cost"])
        materials_list.append(row)

    # Труд (норматив: сдельная оплата по услугам) — по услугам, выбранным для продукта
    labor_list = []
    labor_total = Decimal('0')
    for service in product.services.all():
        unit_price = to_decimal(service.service_price, default='0')
        labor_list.append({
            "service_id": service.id,
            "name": service.name,
            "workshop_id": getattr(service.workshop, 'id', None),
            "workshop_name": getattr(service.workshop, 'name', None),
            "unit_price": qmoney(unit_price),
        })
        labor_total += unit_price

    # При необходимости переопределяем труд фактической себестоимостью труда за единицу
    labor_actual = _actual_labor_per_unit(settings, as_of=as_of)
    labor_source = "services"
    if labor_actual is not None:
        labor_total = qmoney(labor_actual)
        labor_source = "actual_labor"
    else:
        labor_total = qmoney(labor_total)
    materials_total = qmoney(materials_total)

    base = materials_total + labor_total
    overhead_percent = to_decimal(settings.overhead_percent, default='0')
    overhead_from_percent = (base * overhead_percent / Decimal('100')) if overhead_percent else Decimal('0')

    overhead_per_unit_manual = to_decimal(settings.overhead_per_unit, default='0')
    overhead_per_unit_finance = _finance_overhead_per_unit(settings, as_of=as_of)
    overhead_per_unit = overhead_per_unit_manual + overhead_per_unit_finance

    overhead_total = qmoney(overhead_from_percent + overhead_per_unit)
    total_per_unit = qmoney(base + overhead_total)

    totals = {
        "materials": materials_total,
        "labor": labor_total,
        "overhead": overhead_total,
        "total": total_per_unit,
    }

    totals_for_qty = {
        "materials": qmoney(materials_total * Decimal(str(q))),
        "labor": qmoney(labor_total * Decimal(str(q))),
        "overhead": qmoney(overhead_total * Decimal(str(q))),
        "total": qmoney(total_per_unit * Decimal(str(q))),
    }

    return {
        "quantity": q,
        "as_of": (as_of or timezone.localdate()).isoformat(),
        "materials": materials_list,
        "labor": labor_list,
        "totals": totals,
        "totals_for_quantity": totals_for_qty,
        "overhead": {
            "percent": qmoney(overhead_percent),
            "per_unit_manual": qmoney(overhead_per_unit_manual),
            "per_unit_finance": qmoney(overhead_per_unit_finance),
            "period_days": int(settings.overhead_period_days or 30),
            "allocate_from_finance": bool(settings.allocate_overhead_from_finance),
            "labor_source": labor_source,
            "labor_period_days": int(settings.labor_period_days or 30),
            "use_actual_labor": bool(settings.use_actual_labor),
        }
    }




