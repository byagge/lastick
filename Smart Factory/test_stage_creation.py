#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import Order, OrderItem, create_order_stages
from apps.products.models import Product
from apps.clients.models import Client

print("=== Тестирование создания этапов ===")

# Находим клиента
client = Client.objects.first()
if not client:
    print("Нет клиентов в системе")
    exit()

# Находим товар
product = Product.objects.filter(is_glass=False).first()
if not product:
    print("Нет нестеклянных товаров в системе")
    exit()

print(f"Клиент: {client.name}")
print(f"Товар: {product.name}")

# Создаем тестовый заказ
order = Order.objects.create(
    name="Тестовый заказ для проверки этапов",
    client=client,
    status='production'
)

# Создаем позицию заказа
OrderItem.objects.create(
    order=order,
    product=product,
    quantity=10,
    size="80-200",
    color="Белый",
    preparation_specs="Тестовые спецификации для цеха заготовки"
)

print(f"Создан заказ {order.id} с товаром {product.name}")

# Создаем этапы
print("\nСоздание этапов...")
create_order_stages(order)

# Проверяем созданные этапы
from apps.orders.models import OrderStage
stages = OrderStage.objects.filter(order=order)
print(f"\nСоздано этапов: {stages.count()}")

for stage in stages:
    print(f"Этап {stage.id}:")
    print(f"  Цех: {stage.workshop.name if stage.workshop else 'Нет'} (ID: {stage.workshop.id if stage.workshop else 'Нет'})")
    print(f"  Операция: {stage.operation}")
    print(f"  План: {stage.plan_quantity}")
    print(f"  Статус: {stage.status}")
    print(f"  OrderItem: {stage.order_item}")

# Удаляем тестовый заказ
order.delete()
print(f"\nТестовый заказ {order.id} удален")
