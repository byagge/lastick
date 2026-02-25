#!/usr/bin/env python
"""
Простой тест логики расчета штрафов
"""

from datetime import time

def test_time_comparison():
    """Тестирует сравнение времени"""
    
    print("🧪 Тест сравнения времени...")
    
    # Тестовые случаи
    test_times = [
        ("08:30", "До 9:00"),
        ("08:59", "До 9:00"),
        ("09:00", "Ровно 9:00"),
        ("09:01", "После 9:00"),
        ("09:15", "После 9:00"),
        ("10:00", "После 9:00"),
        ("10:18", "После 9:00 (как у Оятилло)"),
        ("10:55", "После 9:00 (как у Сардора)"),
    ]
    
    work_start = time(9, 0)
    
    for time_str, description in test_times:
        hour, minute = map(int, time_str.split(':'))
        check_time = time(hour, minute)
        
        is_late = check_time > work_start
        penalty = 500.00 if is_late else 0.00
        
        status = "🚨 ШТРАФ" if is_late else "✅ БЕЗ ШТРАФА"
        
        print(f"{time_str:>5} → {status:>15} ({penalty:>6.2f} сомов) - {description}")
    
    print(f"\n📋 Логика:")
    print(f"• work_start = {work_start}")
    print(f"• time(10, 18) = {time(10, 18)}")
    print(f"• time(10, 55) = {time(10, 55)}")
    print(f"• time(10, 18) > {work_start} = {time(10, 18) > work_start}")
    print(f"• time(10, 55) > {work_start} = {time(10, 55) > work_start}")

if __name__ == "__main__":
    test_time_comparison() 