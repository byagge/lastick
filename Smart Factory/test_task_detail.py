#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.employee_tasks.models import EmployeeTask
from apps.employee_tasks.serializers import EmployeeTaskSerializer

print("=== Тестирование задачи 211 ===")

try:
    task = EmployeeTask.objects.get(id=211)
    print(f"Задача {task.id}: {task.stage.operation}")
    print(f"  Цех: {task.stage.workshop.name if task.stage.workshop else 'Нет'}")
    print(f"  OrderItem: {task.stage.order_item}")
    
    # Проверяем workshop_info через сериализатор
    serializer = EmployeeTaskSerializer(task)
    data = serializer.data
    print(f"  Workshop info из сериализатора: {data.get('workshop_info', {})}")
    
    # Проверяем, есть ли preparation_specs в OrderItem
    if task.stage.order_item:
        print(f"  OrderItem preparation_specs: {task.stage.order_item.preparation_specs}")
    else:
        print("  OrderItem: None (агрегированный этап)")
        
    # Проверяем все OrderItem в заказе
    if task.stage.order:
        print(f"  Все OrderItem в заказе {task.stage.order.id}:")
        for item in task.stage.order.items.all():
            print(f"    OrderItem {item.id}: {item.product.name if item.product else 'Нет товара'}")
            print(f"      preparation_specs: {item.preparation_specs}")
    
except EmployeeTask.DoesNotExist:
    print("Задача 211 не найдена")

print("\n=== Тестирование задачи 212 ===")

try:
    task = EmployeeTask.objects.get(id=212)
    print(f"Задача {task.id}: {task.stage.operation}")
    print(f"  Цех: {task.stage.workshop.name if task.stage.workshop else 'Нет'}")
    print(f"  OrderItem: {task.stage.order_item}")
    
    # Проверяем workshop_info через сериализатор
    serializer = EmployeeTaskSerializer(task)
    data = serializer.data
    print(f"  Workshop info из сериализатора: {data.get('workshop_info', {})}")
    
    # Проверяем, есть ли preparation_specs в OrderItem
    if task.stage.order_item:
        print(f"  OrderItem preparation_specs: {task.stage.order_item.preparation_specs}")
    else:
        print("  OrderItem: None (агрегированный этап)")
        
    # Проверяем все OrderItem в заказе
    if task.stage.order:
        print(f"  Все OrderItem в заказе {task.stage.order.id}:")
        for item in task.stage.order.items.all():
            print(f"    OrderItem {item.id}: {item.product.name if item.product else 'Нет товара'}")
            print(f"      preparation_specs: {item.preparation_specs}")
    
except EmployeeTask.DoesNotExist:
    print("Задача 212 не найдена")
