#!/usr/bin/env python
"""
Тестовый скрипт для проверки системы посещаемости и штрафов
"""

import os
import sys
import django
from datetime import datetime, time, timedelta

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.attendance.models import AttendanceRecord
from django.contrib.auth import get_user_model

User = get_user_model()

def test_attendance_system():
    """Тестирует систему посещаемости"""
    
    print("🧪 Тестирование системы посещаемости и штрафов...")
    
    # Получаем первого пользователя для тестирования
    try:
        test_user = User.objects.first()
        if not test_user:
            print("❌ Нет пользователей в системе")
            return
        print(f"👤 Тестовый пользователь: {test_user.get_full_name()}")
    except Exception as e:
        print(f"❌ Ошибка получения пользователя: {e}")
        return
    
    # Проверяем существующие записи
    today = datetime.now().date()
    existing_records = AttendanceRecord.objects.filter(
        employee=test_user, 
        date=today
    )
    
    print(f"\n📅 Записи за сегодня ({today}): {existing_records.count()}")
    
    for record in existing_records:
        print(f"  • Время прихода: {record.check_in.time()}")
        print(f"    Опоздание: {record.is_late}")
        print(f"    Штраф: {record.penalty_amount} сомов")
        
        # Проверяем логику
        expected_late = record.check_in.time() > time(9, 0)
        expected_penalty = 500.00 if expected_late else 0.00
        
        if record.is_late != expected_late:
            print(f"    ⚠️  Несоответствие: is_late должно быть {expected_late}")
        
        if record.penalty_amount != expected_penalty:
            print(f"    ⚠️  Несоответствие: penalty_amount должно быть {expected_penalty}")
    
    # Тестируем создание новой записи
    print(f"\n🔄 Тестирование создания новой записи...")
    
    # Создаем тестовую запись с текущим временем
    current_time = datetime.now()
    test_record = AttendanceRecord(
        employee=test_user,
        date=today,
        check_in=current_time
    )
    
    print(f"  Время создания: {current_time.time()}")
    print(f"  Ожидаемое опоздание: {current_time.time() > time(9, 0)}")
    print(f"  Ожидаемый штраф: {500.00 if current_time.time() > time(9, 0) else 0.00}")
    
    # Сохраняем и проверяем
    test_record.save()
    
    print(f"  Результат после сохранения:")
    print(f"    is_late: {test_record.is_late}")
    print(f"    penalty_amount: {test_record.penalty_amount}")
    
    # Удаляем тестовую запись
    test_record.delete()
    print("  ✅ Тестовая запись удалена")
    
    # Проверяем метод recalculate_penalty
    print(f"\n🔄 Тестирование метода recalculate_penalty...")
    
    if existing_records.exists():
        test_record = existing_records.first()
        print(f"  Тестируем запись: {test_record.check_in.time()}")
        
        old_late = test_record.is_late
        old_penalty = test_record.penalty_amount
        
        changed = test_record.recalculate_penalty()
        print(f"  Изменения: {changed}")
        print(f"    is_late: {old_late} → {test_record.is_late}")
        print(f"    penalty_amount: {old_penalty} → {test_record.penalty_amount}")
        
        # Восстанавливаем исходные значения
        test_record.is_late = old_late
        test_record.penalty_amount = old_penalty
        test_record.save()
        print("  ✅ Исходные значения восстановлены")
    
    print(f"\n✅ Тестирование завершено!")

if __name__ == "__main__":
    try:
        test_attendance_system()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 