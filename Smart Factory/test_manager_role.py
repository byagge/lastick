#!/usr/bin/env python
"""
Тестовый скрипт для проверки автоматического изменения ролей
при назначении руководителя цеха
"""

import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.operations.workshops.models import Workshop

def test_manager_role_assignment():
    """Тестирует автоматическое изменение роли при назначении руководителя цеха"""
    
    print("=== Тест автоматического изменения ролей ===\n")
    
    # Создаем тестовых пользователей
    worker1, created = User.objects.get_or_create(
        username='test_worker1',
        defaults={
            'first_name': 'Тестовый',
            'last_name': 'Рабочий 1',
            'role': User.Role.WORKER,
            'phone': '+79001234567',
            'email': 'worker1@test.com'
        }
    )
    
    worker2, created = User.objects.get_or_create(
        username='test_worker2',
        defaults={
            'first_name': 'Тестовый',
            'last_name': 'Рабочий 2',
            'role': User.Role.WORKER,
            'phone': '+79001234568',
            'email': 'worker2@test.com'
        }
    )
    
    # Создаем тестовый цех
    workshop, created = Workshop.objects.get_or_create(
        name='Тестовый цех',
        defaults={
            'description': 'Цех для тестирования',
            'is_active': True
        }
    )
    
    print(f"Создан цех: {workshop.name}")
    print(f"Рабочий 1: {worker1.get_full_name()} (роль: {worker1.get_role_display()})")
    print(f"Рабочий 2: {worker2.get_full_name()} (роль: {worker2.get_role_display()})")
    print()
    
    # Тест 1: Назначаем первого рабочего руководителем
    print("1. Назначаем первого рабочего руководителем цеха...")
    workshop.manager = worker1
    workshop.save()
    
    # Обновляем объекты из базы данных
    worker1.refresh_from_db()
    workshop.refresh_from_db()
    
    print(f"   Результат: {worker1.get_full_name()} теперь {worker1.get_role_display()}")
    print(f"   Руководитель цеха: {workshop.manager.get_full_name() if workshop.manager else 'Не назначен'}")
    print()
    
    # Тест 2: Меняем руководителя на второго рабочего
    print("2. Меняем руководителя на второго рабочего...")
    workshop.manager = worker2
    workshop.save()
    
    # Обновляем объекты из базы данных
    worker1.refresh_from_db()
    worker2.refresh_from_db()
    workshop.refresh_from_db()
    
    print(f"   Результат: {worker1.get_full_name()} теперь {worker1.get_role_display()}")
    print(f"   Результат: {worker2.get_full_name()} теперь {worker2.get_role_display()}")
    print(f"   Руководитель цеха: {workshop.manager.get_full_name() if workshop.manager else 'Не назначен'}")
    print()
    
    # Тест 3: Убираем руководителя
    print("3. Убираем руководителя цеха...")
    workshop.manager = None
    workshop.save()
    
    # Обновляем объекты из базы данных
    worker2.refresh_from_db()
    workshop.refresh_from_db()
    
    print(f"   Результат: {worker2.get_full_name()} теперь {worker2.get_role_display()}")
    print(f"   Руководитель цеха: {workshop.manager.get_full_name() if workshop.manager else 'Не назначен'}")
    print()
    
    # Тест 4: Используем метод set_manager
    print("4. Используем метод set_manager для назначения руководителя...")
    workshop.set_manager(worker1)
    
    # Обновляем объекты из базы данных
    worker1.refresh_from_db()
    workshop.refresh_from_db()
    
    print(f"   Результат: {worker1.get_full_name()} теперь {worker1.get_role_display()}")
    print(f"   Руководитель цеха: {workshop.manager.get_full_name() if workshop.manager else 'Не назначен'}")
    print()
    
    # Проверяем методы пользователя
    print("5. Проверяем методы пользователя:")
    print(f"   {worker1.get_full_name()} является руководителем: {worker1.is_workshop_manager()}")
    print(f"   {worker1.get_full_name()} может быть руководителем: {worker1.can_be_workshop_manager()}")
    managed_workshops = worker1.get_managed_workshops()
    print(f"   Управляемые цеха: {[w.name for w in managed_workshops]}")
    
    print("\n=== Тест завершен ===")

if __name__ == '__main__':
    test_manager_role_assignment() 