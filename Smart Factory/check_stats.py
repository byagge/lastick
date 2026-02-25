#!/usr/bin/env python
"""
Скрипт для проверки статистики сотрудников в БД
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.employees.models import EmployeeStatistics

def check_stats():
    print("Проверка статистики сотрудников...")
    
    # Получаем всех сотрудников
    employees = User.objects.filter(role__in=['worker', 'master', 'admin', 'accountant', 'director', 'founder'])
    print(f"Найдено сотрудников: {employees.count()}")
    
    for employee in employees:
        print(f"\nСотрудник: {employee.get_full_name()} (ID: {employee.id})")
        
        # Проверяем статистику
        try:
            stats = EmployeeStatistics.objects.get(employee=employee)
            print(f"  ✅ Статистика найдена:")
            print(f"    - Выполнено работ: {stats.completed_works}")
            print(f"    - Браки: {stats.defects}")
            print(f"    - Заработок: {stats.monthly_salary}")
            print(f"    - Эффективность: {stats.efficiency}%")
            print(f"    - Производительность: {stats.avg_productivity}")
        except EmployeeStatistics.DoesNotExist:
            print(f"  ❌ Статистика НЕ найдена")
    
    # Общая статистика
    total_stats = EmployeeStatistics.objects.count()
    print(f"\nВсего записей статистики в БД: {total_stats}")

if __name__ == '__main__':
    check_stats() 