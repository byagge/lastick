#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.inventory.models import RawMaterial
from decimal import Decimal

def create_test_materials():
    """Создание тестовых материалов"""
    
    # Очищаем существующие материалы
    RawMaterial.objects.all().delete()
    print("Существующие материалы удалены.")
    
    # Создаем тестовые материалы
    materials_data = [
        {
            'name': 'Сталь листовая',
            'code': 'ST-001',
            'size': '2x1000x2000',
            'unit': 'лист',
            'quantity': 150,
            'min_quantity': 50,
            'price': 2500,
            'description': 'Листовая сталь 2мм для штамповки'
        },
        {
            'name': 'Алюминий профильный',
            'code': 'AL-002',
            'size': '20x20x2000',
            'unit': 'п.м.',
            'quantity': 25,
            'min_quantity': 100,
            'price': 150,
            'description': 'Алюминиевый профиль для конструкций'
        },
        {
            'name': 'Медь листовая',
            'code': 'CU-003',
            'size': '1x500x1000',
            'unit': 'лист',
            'quantity': 80,
            'min_quantity': 30,
            'price': 850,
            'description': 'Медный лист для электротехники'
        },
        {
            'name': 'Пластик ABS',
            'code': 'PL-004',
            'size': '3x1000x2000',
            'unit': 'лист',
            'quantity': 45,
            'min_quantity': 20,
            'price': 320,
            'description': 'ABS пластик для 3D печати'
        },
        {
            'name': 'Резина техническая',
            'code': 'RB-005',
            'size': '5x1000x1000',
            'unit': 'лист',
            'quantity': 12,
            'min_quantity': 25,
            'price': 450,
            'description': 'Техническая резина для уплотнений'
        }
    ]
    
    for data in materials_data:
        material = RawMaterial.objects.create(
            name=data['name'],
            code=data['code'],
            size=data['size'],
            unit=data['unit'],
            quantity=Decimal(str(data['quantity'])),
            min_quantity=Decimal(str(data['min_quantity'])),
            price=Decimal(str(data['price'])),
            description=data['description']
        )
        print(f"Создан материал: {material.name} ({material.code})")
    
    print(f"\nВсего создано материалов: {RawMaterial.objects.count()}")

if __name__ == '__main__':
    create_test_materials() 