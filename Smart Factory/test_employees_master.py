#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы employees_master
"""

import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.operations.workshops.models import Workshop, WorkshopMaster

def test_workshop_access():
    """Тестируем доступ мастеров к цехам"""
    print("=== Тестирование доступа мастеров к цехам ===\n")
    
    # Получаем всех мастеров
    masters = User.objects.filter(role='master')
    print(f"Найдено мастеров: {masters.count()}")
    
    for master in masters:
        print(f"\n--- Мастер: {master.get_full_name()} (ID: {master.id}) ---")
        
        # Цеха где мастер является главным
        managed_workshops = Workshop.objects.filter(manager=master)
        print(f"  Главный мастер цехов: {managed_workshops.count()}")
        for w in managed_workshops:
            print(f"    - {w.name} (ID: {w.id})")
        
        # Цеха где мастер является дополнительным
        additional_workshops = WorkshopMaster.objects.filter(
            master=master, 
            is_active=True
        ).select_related('workshop')
        print(f"  Дополнительный мастер цехов: {additional_workshops.count()}")
        for wm in additional_workshops:
            print(f"    - {wm.workshop.name} (ID: {wm.workshop.id})")
        
        # Общее количество цехов
        all_workshop_ids = set()
        all_workshop_ids.update(managed_workshops.values_list('id', flat=True))
        all_workshop_ids.update([wm.workshop.id for wm in additional_workshops if wm.workshop.is_active])
        
        print(f"  Всего доступно цехов: {len(all_workshop_ids)}")
        print(f"  ID цехов: {list(all_workshop_ids)}")

def test_employees_in_workshops():
    """Тестируем наличие сотрудников в цехах"""
    print("\n=== Тестирование сотрудников в цехах ===\n")
    
    workshops = Workshop.objects.filter(is_active=True)
    print(f"Найдено активных цехов: {workshops.count()}")
    
    for workshop in workshops:
        print(f"\n--- Цех: {workshop.name} (ID: {workshop.id}) ---")
        
        # Сотрудники в цехе
        employees = User.objects.filter(workshop=workshop)
        print(f"  Сотрудников в цехе: {employees.count()}")
        
        for emp in employees[:5]:  # Показываем первые 5
            print(f"    - {emp.get_full_name()} (роль: {emp.get_role_display()})")
        
        if employees.count() > 5:
            print(f"    ... и еще {employees.count() - 5} сотрудников")

if __name__ == '__main__':
    try:
        test_workshop_access()
        test_employees_in_workshops()
        print("\n=== Тестирование завершено ===")
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc() 