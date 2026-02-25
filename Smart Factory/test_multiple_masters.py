#!/usr/bin/env python
"""
Тестовый скрипт для проверки системы нескольких мастеров цехов
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.operations.workshops.models import Workshop, WorkshopMaster
from apps.users.models import User

def test_multiple_masters():
    """Тестирует функциональность нескольких мастеров"""
    print("=== Тестирование системы нескольких мастеров ===\n")
    
    # Получаем все цеха
    workshops = Workshop.objects.all()
    print(f"Найдено цехов: {workshops.count()}")
    
    for workshop in workshops:
        print(f"\n--- Цех: {workshop.name} ---")
        
        # Главный мастер
        if workshop.manager:
            print(f"Главный мастер: {workshop.manager.get_full_name()}")
        else:
            print("Главный мастер: Не назначен")
        
        # Дополнительные мастера
        additional_masters = workshop.workshop_masters.filter(is_active=True)
        print(f"Дополнительных мастеров: {additional_masters.count()}")
        
        for wm in additional_masters:
            print(f"  - {wm.master.get_full_name()} (добавлен: {wm.added_at.strftime('%d.%m.%Y')})")
        
        # Все мастера через метод
        all_masters = workshop.get_all_masters()
        print(f"Всего мастеров: {len(all_masters)}")
        
        # Проверяем метод is_user_master
        if workshop.manager:
            is_main_master = workshop.is_user_master(workshop.manager)
            print(f"Главный мастер является мастером цеха: {is_main_master}")
        
        for wm in additional_masters:
            is_additional_master = workshop.is_user_master(wm.master)
            print(f"Дополнительный мастер {wm.master.get_full_name()} является мастером цеха: {is_additional_master}")

def test_add_remove_masters():
    """Тестирует добавление и удаление мастеров"""
    print("\n=== Тестирование добавления/удаления мастеров ===\n")
    
    # Получаем первый цех
    workshop = Workshop.objects.first()
    if not workshop:
        print("Нет цехов для тестирования")
        return
    
    print(f"Тестируем на цехе: {workshop.name}")
    
    # Получаем пользователя, который не является мастером
    test_user = User.objects.filter(role='worker').first()
    if not test_user:
        print("Нет пользователей с ролью 'worker' для тестирования")
        return
    
    print(f"Тестовый пользователь: {test_user.get_full_name()} (роль: {test_user.get_role_display()})")
    
    # Тестируем добавление мастера
    print(f"\nДобавляем мастера {test_user.get_full_name()} в цех {workshop.name}...")
    success, message = workshop.add_master(test_user)
    print(f"Результат: {message}")
    
    if success:
        print(f"Роль пользователя после добавления: {test_user.get_role_display()}")
        
        # Проверяем, что пользователь стал мастером
        is_master = workshop.is_user_master(test_user)
        print(f"Пользователь является мастером цеха: {is_master}")
        
        # Тестируем удаление мастера
        print(f"\nУдаляем мастера {test_user.get_full_name()} из цеха {workshop.name}...")
        success, message = workshop.remove_master(test_user)
        print(f"Результат: {message}")
        
        if success:
            print(f"Роль пользователя после удаления: {test_user.get_role_display()}")
            
            # Проверяем, что пользователь больше не мастер
            is_master = workshop.is_user_master(test_user)
            print(f"Пользователь является мастером цеха: {is_master}")

def test_workshop_master_model():
    """Тестирует модель WorkshopMaster"""
    print("\n=== Тестирование модели WorkshopMaster ===\n")
    
    # Получаем все связи мастер-цех
    workshop_masters = WorkshopMaster.objects.all()
    print(f"Всего связей мастер-цех: {workshop_masters.count()}")
    
    for wm in workshop_masters:
        print(f"Цех: {wm.workshop.name} | Мастер: {wm.master.get_full_name()} | Активен: {wm.is_active}")
        if wm.added_by:
            print(f"  Добавил: {wm.added_by.get_full_name()}")
        if wm.notes:
            print(f"  Примечания: {wm.notes}")

if __name__ == "__main__":
    try:
        test_multiple_masters()
        test_add_remove_masters()
        test_workshop_master_model()
        print("\n=== Тестирование завершено ===")
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc() 