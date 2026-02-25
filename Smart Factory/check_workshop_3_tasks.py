#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.employee_tasks.models import EmployeeTask
from apps.employee_tasks.serializers import EmployeeTaskSerializer

print("=== Задачи для цеха заготовки (ID 3) ===")

tasks = EmployeeTask.objects.filter(stage__workshop_id=3)
print(f"Задач для цеха 3: {tasks.count()}")

for task in tasks:
    print(f"\nЗадача {task.id}:")
    print(f"  Сотрудник: {task.employee}")
    print(f"  Цех: {task.stage.workshop.name if task.stage.workshop else 'Нет'}")
    print(f"  Операция: {task.stage.operation}")
    print(f"  OrderItem: {task.stage.order_item}")
    print(f"  Количество: {task.quantity}")
    
    # Проверяем workshop_info через сериализатор
    serializer = EmployeeTaskSerializer(task)
    data = serializer.data
    workshop_info = data.get('workshop_info', {})
    print(f"  Workshop info: {workshop_info}")
    
    # Проверяем, есть ли preparation_specs
    if 'preparation_specs' in workshop_info:
        print(f"  ✅ preparation_specs найден: {workshop_info['preparation_specs']}")
    else:
        print(f"  ❌ preparation_specs не найден")
    
    # Проверяем все OrderItem в заказе
    if task.stage.order:
        print(f"  Все OrderItem в заказе {task.stage.order.id}:")
        for item in task.stage.order.items.all():
            print(f"    OrderItem {item.id}: {item.product.name if item.product else 'Нет товара'}")
            print(f"      preparation_specs: {item.preparation_specs}")
            print(f"      size: {item.size}")
            print(f"      color: {item.color}")
