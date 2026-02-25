#!/usr/bin/env python
"""
Скрипт для исправления существующих записей посещаемости и начисления штрафов
"""

import os
import sys
import django
from datetime import time

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.attendance.models import AttendanceRecord
from django.utils import timezone

def fix_existing_penalties():
    """Исправляет штрафы для всех существующих записей с учетом часовых поясов"""
    
    print("🔧 Исправление штрафов для существующих записей...")
    
    # Получаем все записи
    all_records = AttendanceRecord.objects.all()
    print(f"Всего записей: {all_records.count()}")
    
    if all_records.count() == 0:
        print("✅ Нет записей для исправления")
        return
    
    # Анализируем записи
    late_records = []
    on_time_records = []
    
    for record in all_records:
        # Конвертируем UTC время в местное время
        local_check_in = timezone.localtime(record.check_in)
        check_in_time = local_check_in.time()
        work_start_time = time(9, 0)
        
        print(f"DEBUG: {record.employee.get_full_name()} - UTC: {record.check_in}, Local: {local_check_in}, Time: {check_in_time}")
        
        if check_in_time > work_start_time:
            if not record.is_late or record.penalty_amount == 0:
                late_records.append(record)
        else:
            if record.is_late or record.penalty_amount > 0:
                on_time_records.append(record)
    
    print(f"📊 Записей с опозданиями (требуют исправления): {len(late_records)}")
    print(f"📊 Записей вовремя (требуют исправления): {len(on_time_records)}")
    
    if not late_records and not on_time_records:
        print("✅ Все записи уже имеют правильные штрафы!")
        return
    
    # Показываем что будет исправлено
    if late_records:
        print("\n🚨 Записи, которые получат штраф:")
        for record in late_records[:10]:  # Показываем первые 10
            local_time = timezone.localtime(record.check_in)
            print(f"  • {record.employee.get_full_name()} - {record.date} {local_time.time()}")
        if len(late_records) > 10:
            print(f"  ... и еще {len(late_records) - 10} записей")
    
    if on_time_records:
        print("\n✅ Записи, с которых снимут штраф:")
        for record in on_time_records[:10]:  # Показываем первые 10
            local_time = timezone.localtime(record.check_in)
            print(f"  • {record.employee.get_full_name()} - {record.date} {local_time.time()}")
        if len(on_time_records) > 10:
            print(f"  ... и еще {len(on_time_records) - 10} записей")
    
    # Спрашиваем подтверждение
    response = input(f"\n❓ Применить исправления? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Операция отменена")
        return
    
    # Применяем исправления
    print("\n🔄 Применение исправлений...")
    
    updated_count = 0
    
    # Исправляем записи с опозданиями
    for record in late_records:
        old_penalty = record.penalty_amount
        old_is_late = record.is_late
        
        record.is_late = True
        record.penalty_amount = 500.00
        record.save()
        
        updated_count += 1
        local_time = timezone.localtime(record.check_in)
        print(f"  ✓ {record.employee.get_full_name()} - {record.date} {local_time.time()}: "
              f"штраф {old_penalty} → {record.penalty_amount}, опоздание {old_is_late} → {record.is_late}")
    
    # Исправляем записи вовремя
    for record in on_time_records:
        old_penalty = record.penalty_amount
        old_is_late = record.is_late
        
        record.is_late = False
        record.penalty_amount = 0.00
        record.save()
        
        updated_count += 1
        local_time = timezone.localtime(record.check_in)
        print(f"  ✓ {record.employee.get_full_name()} - {record.date} {local_time.time()}: "
              f"штраф {old_penalty} → {record.penalty_amount}, опоздание {old_is_late} → {record.is_late}")
    
    print(f"\n✅ Исправлено записей: {updated_count}")
    print("🎉 Штрафы успешно исправлены!")
    
    # Показываем итоговую статистику
    print(f"\n📊 Итоговая статистика:")
    total_records = AttendanceRecord.objects.count()
    late_count = AttendanceRecord.objects.filter(is_late=True).count()
    total_penalties = sum(record.penalty_amount for record in AttendanceRecord.objects.all())
    
    print(f"  Всего записей: {total_records}")
    print(f"  С опозданиями: {late_count}")
    print(f"  Общая сумма штрафов: {total_penalties} сомов")

if __name__ == "__main__":
    try:
        fix_existing_penalties()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 