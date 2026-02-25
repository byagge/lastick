#!/usr/bin/env python
"""
Тестовый скрипт для проверки автоматической отметки ухода сотрудников
"""

import os
import sys
import django
from datetime import datetime, time

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.utils import timezone
from apps.attendance.models import AttendanceRecord
from apps.users.models import User


def test_auto_checkout():
    """Тестирует автоматическую отметку ухода"""
    print("=== Тест автоматической отметки ухода ===")
    
    # Получаем текущее время
    current_time = timezone.now()
    local_time = timezone.localtime(current_time)
    today = timezone.localdate()
    
    print(f"Текущее время: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Сегодня: {today}")
    
    # Проверяем, есть ли сотрудники на работе
    active_records = AttendanceRecord.objects.filter(
        date=today,
        check_in__isnull=False,
        check_out__isnull=True
    )
    
    print(f"Сотрудников на работе: {active_records.count()}")
    
    if active_records.exists():
        print("\nСотрудники на работе:")
        for record in active_records:
            check_in_local = timezone.localtime(record.check_in)
            print(f"  - {record.employee.get_full_name() or record.employee.username}")
            print(f"    Пришел: {check_in_local.strftime('%H:%M:%S')}")
            print(f"    Опоздание: {'Да' if record.is_late else 'Нет'}")
            print(f"    Штраф: {record.penalty_amount} сомов")
    
    # Проверяем, можно ли выполнить автоматическую отметку ухода
    if local_time.time() >= time(18, 0):
        print(f"\n✅ Время после 18:00 - можно выполнить автоматическую отметку ухода")
        
        # Выполняем автоматическую отметку ухода
        checked_out_count = 0
        for record in active_records:
            record.check_out = current_time
            record.save()
            checked_out_count += 1
            print(f"  ✅ Отмечен уход для {record.employee.get_full_name() or record.employee.username}")
        
        print(f"\n🎉 Автоматически отмечен уход для {checked_out_count} сотрудников")
    else:
        print(f"\n⏰ Время до 18:00 - автоматическая отметка ухода недоступна")
        print(f"   Требуется время: 18:00")
        print(f"   Текущее время: {local_time.strftime('%H:%M')}")
    
    # Показываем статистику
    print(f"\n=== Статистика за сегодня ===")
    total_records = AttendanceRecord.objects.filter(date=today)
    present_today = total_records.count()
    checked_out_today = total_records.filter(check_out__isnull=False).count()
    late_today = total_records.filter(is_late=True).count()
    total_penalties = sum(record.penalty_amount for record in total_records)
    
    print(f"Всего записей: {present_today}")
    print(f"Ушли: {checked_out_today}")
    print(f"На работе: {present_today - checked_out_today}")
    print(f"Опозданий: {late_today}")
    print(f"Общая сумма штрафов: {total_penalties} сомов")


def test_attendance_status():
    """Тестирует получение статуса сотрудников"""
    print("\n=== Тест статуса сотрудников ===")
    
    employees = User.objects.filter(is_active=True)
    today = timezone.localdate()
    
    print(f"Всего активных сотрудников: {employees.count()}")
    
    for employee in employees:
        try:
            record = AttendanceRecord.objects.get(employee=employee, date=today)
            status = 'checked_out' if record.check_out else 'present'
            check_in_time = timezone.localtime(record.check_in) if record.check_in else None
            check_out_time = timezone.localtime(record.check_out) if record.check_out else None
        except AttendanceRecord.DoesNotExist:
            status = 'absent'
            check_in_time = None
            check_out_time = None
        
        status_emoji = {
            'present': '🟢',
            'checked_out': '⚪',
            'absent': '🔴'
        }.get(status, '❓')
        
        print(f"{status_emoji} {employee.get_full_name() or employee.username}: {status}")
        if check_in_time:
            print(f"   Пришел: {check_in_time.strftime('%H:%M')}")
        if check_out_time:
            print(f"   Ушел: {check_out_time.strftime('%H:%M')}")


if __name__ == '__main__':
    test_auto_checkout()
    test_attendance_status() 