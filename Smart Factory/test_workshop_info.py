#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderItem

print("=== Тестирование get_workshop_info ===")

# Находим OrderItem с preparation_specs
items = OrderItem.objects.filter(preparation_specs__isnull=False).exclude(preparation_specs='')
print(f"OrderItem с preparation_specs: {items.count()}")

for item in items[:3]:
    print(f"\nOrderItem {item.id}: {item.product.name if item.product else 'Нет товара'}")
    print(f"  preparation_specs: '{item.preparation_specs}'")
    
    # Тестируем get_workshop_info с разными названиями цехов
    test_workshops = [
        "Заготовка",
        "Заготовительные работы", 
        "Пресс",
        "Заготовительный цех"
    ]
    
    for workshop_name in test_workshops:
        info = item.get_workshop_info(workshop_name)
        has_prep_specs = 'preparation_specs' in info and info['preparation_specs']
        print(f"  {workshop_name}: {'✅' if has_prep_specs else '❌'} {info.get('preparation_specs', 'Нет')}")
