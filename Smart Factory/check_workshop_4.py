#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderStage, OrderItem
from apps.employee_tasks.models import EmployeeTask

print("=== Проверка цеха заготовки (ID 4) ===")

# Проверяем этапы в цехе 4
stages = OrderStage.objects.filter(workshop_id=4)
print(f"Этапов в цехе 4: {stages.count()}")

for stage in stages[:3]:
    print(f"Этап {stage.id}: {stage.operation} - План: {stage.plan_quantity}")
    print(f"  Заказ: {stage.order.name if stage.order else 'Нет'}")
    print(f"  OrderItem: {stage.order_item}")
    
    # Проверяем workshop_info
    workshop_info = stage.get_workshop_info()
    print(f"  Workshop info: {workshop_info}")
    print()

# Проверяем задачи для цеха 4
tasks = EmployeeTask.objects.filter(stage__workshop_id=4)
print(f"Задач для цеха 4: {tasks.count()}")

for task in tasks[:3]:
    print(f"Задача {task.id}: {task.stage.operation}")
    print(f"  Сотрудник: {task.employee}")
    print(f"  Количество: {task.quantity}")
    
    # Проверяем workshop_info через сериализатор
    from apps.employee_tasks.serializers import EmployeeTaskSerializer
    serializer = EmployeeTaskSerializer(task)
    data = serializer.data
    print(f"  Workshop info из сериализатора: {data.get('workshop_info', {})}")
    print()

# Проверяем OrderItem с preparation_specs
items_with_prep = OrderItem.objects.filter(preparation_specs__isnull=False).exclude(preparation_specs='')
print(f"OrderItem с preparation_specs: {items_with_prep.count()}")

for item in items_with_prep[:3]:
    print(f"OrderItem {item.id}: {item.product.name if item.product else 'Нет товара'}")
    print(f"  preparation_specs: {item.preparation_specs}")
    print()
