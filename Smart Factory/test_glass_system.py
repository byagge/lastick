#!/usr/bin/env python
"""
Тестовый скрипт для проверки системы разделения стеклянных заказов
"""
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import Order, OrderItem, OrderStage
from apps.products.models import Product
from apps.clients.models import Client
from apps.operations.workshops.models import Workshop
from apps.orders.models import create_order_stages


def test_glass_system():
    """Тестирует систему разделения стеклянных заказов"""
    print("=== Тестирование системы разделения стеклянных заказов ===\n")
    
    # Проверяем наличие необходимых цехов
    try:
        workshop_1 = Workshop.objects.get(pk=1)
        workshop_2 = Workshop.objects.get(pk=2)
        print(f"✓ Цех 1: {workshop_1.name}")
        print(f"✓ Цех 2: {workshop_2.name}")
    except Workshop.DoesNotExist as e:
        print(f"✗ Ошибка: {e}")
        return
    
    # Получаем или создаем тестового клиента
    client, created = Client.objects.get_or_create(
        name="Тестовый клиент",
        defaults={'phone': '+7-999-999-99-99'}
    )
    
    # Получаем тестовые товары
    try:
        # Обычный товар
        regular_product = Product.objects.filter(is_glass=False).first()
        if not regular_product:
            regular_product = Product.objects.create(
                name="Обычная дверь",
                is_glass=False,
                price=1000
            )
        
        # Стеклянный товар
        glass_product = Product.objects.filter(is_glass=True).first()
        if not glass_product:
            glass_product = Product.objects.create(
                name="Стеклянная дверь",
                is_glass=True,
                glass_type="sandblasted",
                price=2000
            )
        
        print(f"✓ Обычный товар: {regular_product.name}")
        print(f"✓ Стеклянный товар: {glass_product.name}")
        
    except Exception as e:
        print(f"✗ Ошибка создания товаров: {e}")
        return
    
    # Тест 1: Заказ только с обычными товарами
    print("\n--- Тест 1: Заказ только с обычными товарами ---")
    order_regular = Order.objects.create(
        name="Тестовый заказ - только обычные товары",
        client=client,
        status='production'
    )
    
    OrderItem.objects.create(
        order=order_regular,
        product=regular_product,
        quantity=2,
        size="2000x800"
    )
    
    create_order_stages(order_regular)
    
    stages = order_regular.stages.all()
    print(f"Создано этапов: {stages.count()}")
    for stage in stages:
        print(f"  - {stage.workshop.name}: {stage.operation} (кол-во: {stage.plan_quantity})")
    
    # Тест 2: Заказ только со стеклянными товарами
    print("\n--- Тест 2: Заказ только со стеклянными товарами ---")
    order_glass = Order.objects.create(
        name="Тестовый заказ - только стеклянные товары",
        client=client,
        status='production'
    )
    
    OrderItem.objects.create(
        order=order_glass,
        product=glass_product,
        quantity=1,
        size="2000x800"
    )
    
    create_order_stages(order_glass)
    
    stages = order_glass.stages.all()
    print(f"Создано этапов: {stages.count()}")
    for stage in stages:
        print(f"  - {stage.workshop.name}: {stage.operation} (кол-во: {stage.plan_quantity})")
    
    # Тест 3: Смешанный заказ
    print("\n--- Тест 3: Смешанный заказ ---")
    order_mixed = Order.objects.create(
        name="Тестовый заказ - смешанный",
        client=client,
        status='production'
    )
    
    OrderItem.objects.create(
        order=order_mixed,
        product=regular_product,
        quantity=1,
        size="2000x800"
    )
    
    OrderItem.objects.create(
        order=order_mixed,
        product=glass_product,
        quantity=1,
        size="2000x800"
    )
    
    create_order_stages(order_mixed)
    
    stages = order_mixed.stages.all()
    print(f"Создано этапов: {stages.count()}")
    for stage in stages:
        print(f"  - {stage.workshop.name}: {stage.operation} (кол-во: {stage.plan_quantity})")
    
    # Проверяем свойства заказов
    print("\n--- Проверка свойств заказов ---")
    print(f"Заказ {order_regular.id}: has_glass_items = {order_regular.has_glass_items}")
    print(f"Заказ {order_glass.id}: has_glass_items = {order_glass.has_glass_items}")
    print(f"Заказ {order_mixed.id}: has_glass_items = {order_mixed.has_glass_items}")
    
    print(f"Заказ {order_mixed.id}: glass_items = {len(order_mixed.glass_items)}")
    print(f"Заказ {order_mixed.id}: regular_items = {len(order_mixed.regular_items)}")
    
    # Очистка тестовых данных
    print("\n--- Очистка тестовых данных ---")
    order_regular.delete()
    order_glass.delete()
    order_mixed.delete()
    print("✓ Тестовые заказы удалены")
    
    print("\n=== Тестирование завершено ===")


if __name__ == "__main__":
    test_glass_system() 