#!/usr/bin/env python
"""
Скрипт для тестирования приложения "Онлайн пользователи"
"""

import os
import sys
import django
from datetime import datetime

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.online.models import UserActivity
from django.utils import timezone

User = get_user_model()

def test_online_app():
    """Тестирование основных функций приложения"""
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ ПРИЛОЖЕНИЯ 'ОНЛАЙН ПОЛЬЗОВАТЕЛИ'")
    print("=" * 50)
    
    # 1. Проверяем существующих пользователей
    print("\n1. Проверка существующих пользователей:")
    users = User.objects.all()
    print(f"   Всего пользователей в системе: {users.count()}")
    
    for user in users[:5]:  # Показываем первые 5
        print(f"   - {user.username} (staff: {user.is_staff}, superuser: {user.is_superuser})")
    
    if users.count() > 5:
        print(f"   ... и еще {users.count() - 5} пользователей")
    
    # 2. Проверяем записи активности
    print("\n2. Проверка записей активности:")
    activities = UserActivity.objects.all()
    print(f"   Всего записей активности: {activities.count()}")
    
    if activities.exists():
        print("   Последние записи активности:")
        for activity in activities.order_by('-last_seen')[:3]:
            print(f"   - {activity.user.username}: {activity.last_seen} (онлайн: {activity.is_online})")
    else:
        print("   Записей активности нет")
    
    # 3. Тестируем методы модели
    print("\n3. Тестирование методов модели:")
    
    # Получаем онлайн пользователей
    online_users = UserActivity.get_online_users()
    print(f"   Онлайн пользователей: {online_users.count()}")
    
    if online_users.exists():
        print("   Список онлайн пользователей:")
        for activity in online_users:
            print(f"   - {activity.user.username} (последняя активность: {activity.last_seen})")
    
    # 4. Создаем тестовую запись активности для первого пользователя
    if users.exists():
        test_user = users.first()
        print(f"\n4. Создание тестовой записи активности для {test_user.username}:")
        
        try:
            activity = UserActivity.update_user_activity(test_user)
            print(f"   Запись активности обновлена: {activity.last_seen}")
        except Exception as e:
            print(f"   Ошибка при обновлении активности: {e}")
    
    # 5. Проверяем статистику
    print("\n5. Статистика:")
    total_users = User.objects.count()
    total_activities = UserActivity.objects.count()
    online_count = UserActivity.get_online_users().count()
    
    print(f"   Всего пользователей: {total_users}")
    print(f"   Всего записей активности: {total_activities}")
    print(f"   Онлайн сейчас: {online_count}")
    
    if total_users > 0:
        coverage = (total_activities / total_users) * 100
        print(f"   Покрытие активности: {coverage:.1f}%")
    
    print("\n" + "=" * 50)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 50)

def create_sample_activities():
    """Создание образцовых записей активности для всех пользователей"""
    print("\nСоздание образцовых записей активности...")
    
    users = User.objects.all()
    created_count = 0
    updated_count = 0
    
    for user in users:
        try:
            activity, created = UserActivity.objects.get_or_create(
                user=user,
                defaults={
                    'last_seen': timezone.now(),
                    'is_online': True
                }
            )
            
            if created:
                created_count += 1
                print(f"   Создана запись для {user.username}")
            else:
                # Обновляем существующую запись
                activity.last_seen = timezone.now()
                activity.is_online = True
                activity.save()
                updated_count += 1
                print(f"   Обновлена запись для {user.username}")
                
        except Exception as e:
            print(f"   Ошибка для {user.username}: {e}")
    
    print(f"\nРезультат: создано {created_count}, обновлено {updated_count}")

if __name__ == "__main__":
    try:
        # Основное тестирование
        test_online_app()
        
        # Создание образцовых записей активности
        create_sample_activities()
        
        # Повторное тестирование после создания записей
        print("\n" + "=" * 50)
        print("ПОВТОРНОЕ ТЕСТИРОВАНИЕ ПОСЛЕ СОЗДАНИЯ ЗАПИСЕЙ")
        print("=" * 50)
        test_online_app()
        
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback
        traceback.print_exc() 