#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderStage, OrderItem
from apps.employee_tasks.models import EmployeeTask

def fix_stages():
    print("=== Исправление связи этапов с позициями заказа ===")
    
    # Находим этапы без позиций заказа
    stages_without_items = OrderStage.objects.filter(order_item__isnull=True)
    print(f"Этапов без позиций заказа: {stages_without_items.count()}")
    
    # Находим позиции заказа без этапов
    order_items = OrderItem.objects.all()
    print(f"Всего позиций заказа: {order_items.count()}")
    
    # Для каждого этапа без позиции заказа пытаемся найти подходящую позицию
    for stage in stages_without_items:
        print(f"\nОбрабатываем этап: {stage}")
        print(f"  - Заказ: {stage.order}")
        
        # Ищем позиции заказа для этого заказа
        items_for_order = OrderItem.objects.filter(order=stage.order)
        print(f"  - Позиций для заказа: {items_for_order.count()}")
        
        if items_for_order.exists():
            # Берем первую позицию заказа
            item = items_for_order.first()
            print(f"  - Связываем с позицией: {item}")
            
            # Обновляем этап
            stage.order_item = item
            stage.save()
            print(f"  - ✅ Этап обновлен!")
        else:
            print(f"  - ❌ Нет позиций заказа для этого заказа")
    
    # Проверяем результат
    print(f"\n=== Результат ===")
    stages_with_items = OrderStage.objects.filter(order_item__isnull=False)
    print(f"Этапов с позициями заказа: {stages_with_items.count()}")
    
    tasks_with_items = EmployeeTask.objects.filter(stage__order_item__isnull=False)
    print(f"Задач с позициями заказа: {tasks_with_items.count()}")

if __name__ == '__main__':
    fix_stages() 