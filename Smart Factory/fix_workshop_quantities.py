#!/usr/bin/env python
"""
Скрипт для исправления количества в этапах заказов для цехов с ID >= 6.
Исправляет plan_quantity для агрегированных этапов, чтобы показывать только количество нестеклянных товаров.
"""

import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.orders.models import Order, OrderStage, OrderItem
from apps.operations.workshops.models import Workshop
from django.db import transaction

def fix_workshop_quantities():
    """
    Исправляет количество в этапах заказов для цехов с ID >= 6.
    Для агрегированных этапов (order_item=None) устанавливает количество только нестеклянных товаров.
    """
    
    print("Начинаем исправление количества в этапах заказов...")
    
    # Получаем все цеха с ID >= 6
    workshops_6_plus = Workshop.objects.filter(id__gte=6)
    print(f"Найдено цехов с ID >= 6: {workshops_6_plus.count()}")
    
    # Получаем все агрегированные этапы в цехах с ID >= 6
    aggregated_stages = OrderStage.objects.filter(
        workshop__id__gte=6,
        order_item__isnull=True,  # Агрегированные этапы
        stage_type='workshop'
    ).select_related('order', 'workshop')
    
    print(f"Найдено агрегированных этапов в цехах >= 6: {aggregated_stages.count()}")
    
    fixed_count = 0
    error_count = 0
    
    with transaction.atomic():
        for stage in aggregated_stages:
            try:
                # Вычисляем количество только нестеклянных товаров в заказе
                non_glass_quantity = sum(
                    item.quantity for item in stage.order.items.filter(product__is_glass=False)
                )
                
                # Обновляем plan_quantity только если количество изменилось
                if stage.plan_quantity != non_glass_quantity:
                    old_quantity = stage.plan_quantity
                    stage.plan_quantity = non_glass_quantity
                    stage.save(update_fields=['plan_quantity'])
                    
                    print(f"Исправлен этап ID {stage.id} в цехе '{stage.workshop.name}' (заказ {stage.order.id}): {old_quantity} -> {non_glass_quantity}")
                    fixed_count += 1
                else:
                    print(f"Этап ID {stage.id} уже имеет правильное количество: {stage.plan_quantity}")
                    
            except Exception as e:
                print(f"Ошибка при исправлении этапа ID {stage.id}: {str(e)}")
                error_count += 1
    
    print(f"\nИсправление завершено:")
    print(f"- Исправлено этапов: {fixed_count}")
    print(f"- Ошибок: {error_count}")
    
    return fixed_count, error_count

def fix_individual_stages():
    """
    Исправляет количество в индивидуальных этапах (с order_item) в цехах с ID >= 6.
    Удаляет этапы со стеклянными товарами и корректирует количество для нестеклянных.
    """
    
    print("\nНачинаем исправление индивидуальных этапов...")
    
    # Получаем все индивидуальные этапы в цехах с ID >= 6
    individual_stages = OrderStage.objects.filter(
        workshop__id__gte=6,
        order_item__isnull=False,  # Индивидуальные этапы
        stage_type='workshop'
    ).select_related('order', 'workshop', 'order_item__product')
    
    print(f"Найдено индивидуальных этапов в цехах >= 6: {individual_stages.count()}")
    
    deleted_count = 0
    fixed_count = 0
    error_count = 0
    
    with transaction.atomic():
        for stage in individual_stages:
            try:
                if stage.order_item and stage.order_item.product.is_glass:
                    # Удаляем этапы со стеклянными товарами
                    stage.delete()
                    print(f"Удален этап ID {stage.id} со стеклянным товаром в цехе '{stage.workshop.name}'")
                    deleted_count += 1
                else:
                    # Для нестеклянных товаров проверяем, что количество правильное
                    if stage.order_item and not stage.order_item.product.is_glass:
                        if stage.plan_quantity != stage.order_item.quantity:
                            old_quantity = stage.plan_quantity
                            stage.plan_quantity = stage.order_item.quantity
                            stage.save(update_fields=['plan_quantity'])
                            print(f"Исправлено количество этапа ID {stage.id}: {old_quantity} -> {stage.plan_quantity}")
                            fixed_count += 1
                    
            except Exception as e:
                print(f"Ошибка при обработке этапа ID {stage.id}: {str(e)}")
                error_count += 1
    
    print(f"\nИсправление индивидуальных этапов завершено:")
    print(f"- Удалено этапов со стеклянными товарами: {deleted_count}")
    print(f"- Исправлено этапов: {fixed_count}")
    print(f"- Ошибок: {error_count}")
    
    return deleted_count, fixed_count, error_count

def show_statistics():
    """
    Показывает статистику по заказам и этапам
    """
    
    print("\n=== СТАТИСТИКА ===")
    
    # Общая статистика по заказам
    total_orders = Order.objects.count()
    orders_with_glass = Order.objects.filter(items__product__is_glass=True).distinct().count()
    orders_with_regular = Order.objects.filter(items__product__is_glass=False).distinct().count()
    
    print(f"Всего заказов: {total_orders}")
    print(f"Заказов со стеклянными товарами: {orders_with_glass}")
    print(f"Заказов с обычными товарами: {orders_with_regular}")
    
    # Статистика по этапам в цехах >= 6
    stages_6_plus = OrderStage.objects.filter(workshop__id__gte=6, stage_type='workshop')
    aggregated_stages = stages_6_plus.filter(order_item__isnull=True)
    individual_stages = stages_6_plus.filter(order_item__isnull=False)
    
    print(f"\nЭтапы в цехах >= 6:")
    print(f"- Всего этапов: {stages_6_plus.count()}")
    print(f"- Агрегированных: {aggregated_stages.count()}")
    print(f"- Индивидуальных: {individual_stages.count()}")
    
    # Статистика по товарам
    total_items = OrderItem.objects.count()
    glass_items = OrderItem.objects.filter(product__is_glass=True).count()
    regular_items = OrderItem.objects.filter(product__is_glass=False).count()
    
    print(f"\nТовары в заказах:")
    print(f"- Всего позиций: {total_items}")
    print(f"- Стеклянных: {glass_items}")
    print(f"- Обычных: {regular_items}")

if __name__ == "__main__":
    print("=== СКРИПТ ИСПРАВЛЕНИЯ КОЛИЧЕСТВА В ЭТАПАХ ЗАКАЗОВ ===")
    
    # Показываем статистику до исправления
    show_statistics()
    
    # Исправляем агрегированные этапы
    fixed_aggregated, errors_aggregated = fix_workshop_quantities()
    
    # Исправляем индивидуальные этапы
    deleted_individual, fixed_individual, errors_individual = fix_individual_stages()
    
    # Показываем статистику после исправления
    print("\n=== СТАТИСТИКА ПОСЛЕ ИСПРАВЛЕНИЯ ===")
    show_statistics()
    
    print(f"\n=== ИТОГИ ===")
    print(f"Исправлено агрегированных этапов: {fixed_aggregated}")
    print(f"Удалено этапов со стеклянными товарами: {deleted_individual}")
    print(f"Исправлено индивидуальных этапов: {fixed_individual}")
    print(f"Всего ошибок: {errors_aggregated + errors_individual}")
    
    print("\nСкрипт завершен!")