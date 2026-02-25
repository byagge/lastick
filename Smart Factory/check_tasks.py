#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderStage
from apps.employee_tasks.models import EmployeeTask

print("=== Проверка задач для этапа 10 ===")

# Проверяем этап 10
try:
    stage = OrderStage.objects.get(id=10)
    print(f"Этап {stage.id}: {stage.operation}")
    print(f"  Цех: {stage.workshop.name if stage.workshop else 'Нет'}")
    print(f"  Заказ: {stage.order.name if stage.order else 'Нет'}")
    print(f"  OrderItem: {stage.order_item}")
    
    # Проверяем workshop_info
    workshop_info = stage.get_workshop_info()
    print(f"  Workshop info: {workshop_info}")
    print()
    
    # Проверяем задачи для этого этапа
    tasks = EmployeeTask.objects.filter(stage=stage)
    print(f"Задач для этапа {stage.id}: {tasks.count()}")
    
    for task in tasks:
        print(f"Задача {task.id}:")
        print(f"  Сотрудник: {task.employee}")
        print(f"  Количество: {task.quantity}")
        
        # Проверяем workshop_info через сериализатор
        from apps.employee_tasks.serializers import EmployeeTaskSerializer
        serializer = EmployeeTaskSerializer(task)
        data = serializer.data
        print(f"  Workshop info из сериализатора: {data.get('workshop_info', {})}")
        print()
        
except OrderStage.DoesNotExist:
    print("Этап 10 не найден")
