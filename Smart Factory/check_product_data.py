#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.products.models import Product
from apps.orders.models import OrderItem
from apps.employee_tasks.models import EmployeeTask

def check_product_data():
    print("=== Проверка данных о товарах ===")
    
    # Проверяем товары
    products = Product.objects.all()
    print(f"Всего товаров: {products.count()}")
    
    for product in products:
        print(f"\nТовар: {product.name}")
        print(f"  - Тип: {product.type}")
        print(f"  - Стеклянный: {product.is_glass}")
        print(f"  - Тип стекла: {product.glass_type}")
        print(f"  - Изображение: {product.img}")
        print(f"  - URL изображения: {product.img.url if product.img else 'Нет'}")
        print(f"  - Цена: {product.price}")
    
    # Проверяем позиции заказов
    print(f"\n=== Проверка позиций заказов ===")
    order_items = OrderItem.objects.all()
    print(f"Всего позиций заказов: {order_items.count()}")
    
    for item in order_items:
        print(f"\nПозиция заказа: {item}")
        print(f"  - Товар: {item.product}")
        print(f"  - Размер: {item.size}")
        print(f"  - Цвет: {item.color}")
        print(f"  - Тип стекла: {item.glass_type}")
        print(f"  - Тип краски: {item.paint_type}")
        print(f"  - Цвет краски: {item.paint_color}")
        if item.product:
            print(f"  - Товар стеклянный: {item.product.is_glass}")
            print(f"  - Изображение товара: {item.product.img}")
    
    # Проверяем задачи сотрудников
    print(f"\n=== Проверка задач сотрудников ===")
    tasks = EmployeeTask.objects.all()
    print(f"Всего задач: {tasks.count()}")
    
    for task in tasks:
        print(f"\nЗадача: {task}")
        print(f"  - Сотрудник: {task.employee}")
        print(f"  - Этап: {task.stage}")
        if task.stage and task.stage.order_item:
            print(f"  - Позиция заказа: {task.stage.order_item}")
            print(f"  - Товар: {task.stage.order_item.product}")
            if task.stage.order_item.product:
                print(f"  - Изображение: {task.stage.order_item.product.img}")
        else:
            print(f"  - Нет связанной позиции заказа")

if __name__ == '__main__':
    check_product_data() 