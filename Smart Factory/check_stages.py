#!/usr/bin/env python
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import OrderStage, Order, OrderItem

# Check all stages
print("All stages:")
stages = OrderStage.objects.all()
for s in stages:
    print(f"Stage {s.id}: order={s.order}, order_item={s.order_item}, workshop={s.workshop}, status={s.status}")

print("\nStages with null order_item:")
null_stages = OrderStage.objects.filter(order_item__isnull=True)
for s in null_stages:
    print(f"Stage {s.id}: order={s.order}, workshop={s.workshop}, status={s.status}")

print("\nStages in workshop 1 with status in_progress:")
in_progress_stages = OrderStage.objects.filter(workshop_id=1, status='in_progress')
for s in in_progress_stages:
    print(f"Stage {s.id}: order={s.order}, order_item={s.order_item}, workshop={s.workshop}, status={s.status}")

# Check all orders with their items
print("\nAll orders:")
orders = Order.objects.all()
for order in orders:
    print(f"Order {order.id} ({order.name}):")
    print(f"  Items count: {order.items.count()}")
    print(f"  Stages count: {order.stages.count()}")
    if order.items.exists():
        for item in order.items.all():
            print(f"    Item {item.id}: {item.product.name if item.product else 'No product'}")
    print() 