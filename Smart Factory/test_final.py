#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.employee_tasks.models import EmployeeTask
from apps.employee_tasks.serializers import EmployeeTaskSerializer

print("=== Тестирование задач для цехов 3 и 4 ===")

# Проверяем задачи для цехов 3 и 4
for workshop_id in [3, 4]:
    tasks = EmployeeTask.objects.filter(stage__workshop_id=workshop_id)
    print(f"\nЦех ID {workshop_id}: {tasks.count()} задач")
    
    for task in tasks[:2]:  # Берем первые 2 задачи
        print(f"  Задача {task.id}: {task.stage.operation}")
        print(f"    Цех: {task.stage.workshop.name}")
        
        # Проверяем workshop_info через сериализатор
        serializer = EmployeeTaskSerializer(task)
        data = serializer.data
        workshop_info = data.get('workshop_info', {})
        
        if 'preparation_specs' in workshop_info:
            print(f"    ✅ preparation_specs: {workshop_info['preparation_specs']}")
        else:
            print(f"    ❌ preparation_specs не найден")
            print(f"    Workshop info keys: {list(workshop_info.keys())}")
