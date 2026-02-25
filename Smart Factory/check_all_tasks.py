#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.employee_tasks.models import EmployeeTask

print("=== Все задачи в системе ===")

tasks = EmployeeTask.objects.all().order_by('-id')[:10]
print(f"Всего задач: {EmployeeTask.objects.count()}")
print("Последние 10 задач:")

for task in tasks:
    print(f"Задача {task.id}:")
    print(f"  Сотрудник: {task.employee}")
    print(f"  Цех: {task.stage.workshop.name if task.stage.workshop else 'Нет'}")
    print(f"  Операция: {task.stage.operation}")
    print(f"  OrderItem: {task.stage.order_item}")
    print(f"  Количество: {task.quantity}")
    print()
