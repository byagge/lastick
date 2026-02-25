#!/usr/bin/env python
"""
Скрипт для пересчета штрафов за опоздания
Запускать из корневой директории проекта Django
"""

import os
import sys
import django
from datetime import time

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.attendance.models import AttendanceRecord

def recalculate_all_penalties():
    """Пересчитывает штрафы для всех записей посещаемости"""
    
    print("🔍 Анализ записей посещаемости...")
    
    # Получаем все записи
    all_records = AttendanceRecord.objects.all()
    print(f"Всего записей: {all_records.count()}")
    
    # Анализируем записи
    late_records = []
    on_time_records = []
    
    for record in all_records:
        check_in_time = record.check_in.time()
        work_start_time = time(9, 0)
        
        if check_in_time > work_start_time:
            if not record.is_late or record.penalty_amount == 0:
                late_records.append(record)
        else:
            if record.is_late or record.penalty_amount > 0:
                on_time_records.append(record)
    
    print(f"📊 Найдено записей с опозданиями: {len(late_records)}")
    print(f"📊 Найдено записей вовремя: {len(on_time_records)}")
    
    if not late_records and not on_time_records:
        print("✅ Все записи уже имеют правильные штрафы!")
        return
    
    # Показываем что будет изменено
    if late_records:
        print("\n🚨 Записи, которые получат штраф:")
        for record in late_records[:5]:  # Показываем первые 5
            print(f"  • {record.employee.get_full_name()} - {record.date} {record.check_in.time()}")
        if len(late_records) > 5:
            print(f"  ... и еще {len(late_records) - 5} записей")
    
    if on_time_records:
        print("\n✅ Записи, с которых снимут штраф:")
        for record in on_time_records[:5]:  # Показываем первые 5
            print(f"  • {record.employee.get_full_name()} - {record.date} {record.check_in.time()}")
        if len(on_time_records) > 5:
            print(f"  ... и еще {len(on_time_records) - 5} записей")
    
    # Спрашиваем подтверждение
    response = input(f"\n❓ Применить изменения? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Операция отменена")
        return
    
    # Применяем изменения
    print("\n🔄 Применение изменений...")
    
    updated_count = 0
    
    # Обновляем записи с опозданиями
    for record in late_records:
        old_penalty = record.penalty_amount
        old_is_late = record.is_late
        
        record.calculate_penalty()
        record.save()
        
        if old_penalty != record.penalty_amount or old_is_late != record.is_late:
            updated_count += 1
            print(f"  ✓ {record.employee.get_full_name()} - {record.date} {record.check_in.time()}: "
                  f"штраф {old_penalty} → {record.penalty_amount}, опоздание {old_is_late} → {record.is_late}")
    
    # Обновляем записи вовремя
    for record in on_time_records:
        old_penalty = record.penalty_amount
        old_is_late = record.is_late
        
        record.calculate_penalty()
        record.save()
        
        if old_penalty != record.penalty_amount or old_is_late != record.is_late:
            updated_count += 1
            print(f"  ✓ {record.employee.get_full_name()} - {record.date} {record.check_in.time()}: "
                  f"штраф {old_penalty} → {record.penalty_amount}, опоздание {old_is_late} → {record.is_late}")
    
    print(f"\n✅ Обновлено записей: {updated_count}")
    print("🎉 Штрафы успешно пересчитаны!")

if __name__ == "__main__":
    try:
        recalculate_all_penalties()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1) 