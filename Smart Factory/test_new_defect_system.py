#!/usr/bin/env python
"""
Скрипт для тестирования новой системы браков
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.defects.models import Defect
from apps.employee_tasks.models import EmployeeTask
from apps.users.models import User
from apps.products.models import Product
from apps.orders.models import Order, OrderItem, OrderStage
from apps.operations.workshops.models import Workshop
from apps.services.models import Service
from decimal import Decimal

def test_new_defect_system():
    """Тестирует новую систему браков"""
    print("=== Тестирование новой системы браков ===\n")
    
    # 1. Проверяем существующие данные
    print("1. Проверка существующих данных:")
    total_defects = Defect.objects.count()
    total_tasks = EmployeeTask.objects.count()
    print(f"   - Всего браков в системе: {total_defects}")
    print(f"   - Всего задач сотрудников: {total_tasks}")
    
    # 2. Создаем тестовые данные
    print("\n2. Создание тестовых данных:")
    
    # Получаем или создаем цех
    workshop, created = Workshop.objects.get_or_create(
        name="Тестовый цех",
        defaults={'description': 'Цех для тестирования'}
    )
    print(f"   - Цех: {workshop.name} ({'создан' if created else 'существовал'})")
    
    # Получаем или создаем продукт
    product, created = Product.objects.get_or_create(
        name="Тестовый продукт",
        defaults={'code': 'TEST001', 'description': 'Продукт для тестирования'}
    )
    print(f"   - Продукт: {product.name} ({'создан' if created else 'существовал'})")
    
    # Получаем или создаем услугу
    service, created = Service.objects.get_or_create(
        name="Тестовая услуга",
        workshop=workshop,
        defaults={
            'service_price': Decimal('100.00'),
            'defect_penalty': Decimal('50.00'),
            'is_active': True
        }
    )
    print(f"   - Услуга: {service.name} ({'создана' if created else 'существовала'})")
    
    # Получаем или создаем пользователя
    user, created = User.objects.get_or_create(
        username='test_employee',
        defaults={
            'first_name': 'Тест',
            'last_name': 'Сотрудник',
            'role': 'employee',
            'workshop': workshop
        }
    )
    print(f"   - Сотрудник: {user.get_full_name()} ({'создан' if created else 'существовал'})")
    
    # Получаем или создаем мастера
    master, created = User.objects.get_or_create(
        username='test_master',
        defaults={
            'first_name': 'Тест',
            'last_name': 'Мастер',
            'role': 'master',
            'workshop': workshop
        }
    )
    print(f"   - Мастер: {master.get_full_name()} ({'создан' if created else 'существовал'})")
    
    # 3. Создаем тестовый заказ и задачу
    print("\n3. Создание тестового заказа и задачи:")
    
    # Создаем заказ
    order, created = Order.objects.get_or_create(
        name="Тестовый заказ",
        defaults={
            'client_id': 1,  # Предполагаем, что клиент с ID 1 существует
            'status': 'in_progress'
        }
    )
    print(f"   - Заказ: {order.name} ({'создан' if created else 'существовал'})")
    
    # Создаем элемент заказа
    order_item, created = OrderItem.objects.get_or_create(
        order=order,
        product=product,
        defaults={'quantity': 10}
    )
    print(f"   - Элемент заказа: {order_item.product.name} x{order_item.quantity} ({'создан' if created else 'существовал'})")
    
    # Создаем этап заказа
    stage, created = OrderStage.objects.get_or_create(
        order=order,
        workshop=workshop,
        defaults={
            'operation': 'Тестовая операция',
            'quantity': 10,
            'completed_quantity': 0,
            'status': 'in_progress'
        }
    )
    print(f"   - Этап заказа: {stage.operation} ({'создан' if created else 'существовал'})")
    
    # Создаем задачу сотрудника
    task, created = EmployeeTask.objects.get_or_create(
        stage=stage,
        employee=user,
        defaults={
            'quantity': 10,
            'completed_quantity': 5,
            'defective_quantity': 0  # Начинаем с 0 браков
        }
    )
    print(f"   - Задача сотрудника: {task.employee.get_full_name()} - {task.stage.operation} ({'создана' if created else 'существовала'})")
    
    # 4. Тестируем создание брака
    print("\n4. Тестирование создания брака:")
    
    # Увеличиваем количество браков в задаче
    old_defective_quantity = task.defective_quantity
    task.defective_quantity = 2
    task.save()
    print(f"   - Увеличили defective_quantity с {old_defective_quantity} до {task.defective_quantity}")
    
    # Проверяем, что создались записи браков
    new_defects = Defect.objects.filter(employee_task=task)
    print(f"   - Создано записей браков: {new_defects.count()}")
    
    for defect in new_defects:
        print(f"     * Брак #{defect.id}: {defect.product.name} - {defect.get_status_display()}")
    
    # 5. Тестируем подтверждение брака мастером
    print("\n5. Тестирование подтверждения брака мастером:")
    
    if new_defects.exists():
        defect = new_defects.first()
        print(f"   - Подтверждаем брак #{defect.id}")
        
        try:
            # Подтверждаем как технический брак (без штрафа)
            defect.confirm_defect(
                master=master,
                is_repairable=False,
                defect_type='technical',
                comment='Тестовое подтверждение технического брака'
            )
            print(f"     * Статус изменен на: {defect.get_status_display()}")
            print(f"     * Тип брака: {defect.get_defect_type_display()}")
            print(f"     * Штраф применен: {defect.penalty_applied}")
            print(f"     * Сумма штрафа: {defect.penalty_amount}")
            
            # Проверяем, что штраф не применился к задаче
            task.refresh_from_db()
            print(f"     * Штраф в задаче: {task.penalties}")
            
        except Exception as e:
            print(f"     * Ошибка при подтверждении: {e}")
    
    # 6. Тестируем ручной брак со штрафом
    print("\n6. Тестирование ручного брака со штрафом:")
    
    if new_defects.count() > 1:
        defect = new_defects[1]
        print(f"   - Подтверждаем брак #{defect.id} как ручной")
        
        try:
            # Подтверждаем как ручной брак (со штрафом)
            defect.confirm_defect(
                master=master,
                is_repairable=False,
                defect_type='manual',
                comment='Тестовое подтверждение ручного брака'
            )
            print(f"     * Статус изменен на: {defect.get_status_display()}")
            print(f"     * Тип брака: {defect.get_defect_type_display()}")
            print(f"     * Штраф применен: {defect.penalty_applied}")
            print(f"     * Сумма штрафа: {defect.penalty_amount}")
            
            # Проверяем, что штраф применился к задаче
            task.refresh_from_db()
            print(f"     * Штраф в задаче: {task.penalties}")
            print(f"     * Чистый заработок: {task.net_earnings}")
            
        except Exception as e:
            print(f"     * Ошибка при подтверждении: {e}")
    
    # 7. Итоговая статистика
    print("\n7. Итоговая статистика:")
    total_defects_after = Defect.objects.count()
    pending_defects = Defect.objects.filter(status='pending').count()
    confirmed_defects = Defect.objects.filter(status='confirmed').count()
    irreparable_defects = Defect.objects.filter(status='irreparable').count()
    
    print(f"   - Всего браков: {total_defects_after}")
    print(f"   - Ожидают подтверждения: {pending_defects}")
    print(f"   - Подтверждены: {confirmed_defects}")
    print(f"   - Неисправимые: {irreparable_defects}")
    
    print("\n=== Тестирование завершено ===")

if __name__ == '__main__':
    test_new_defect_system() 