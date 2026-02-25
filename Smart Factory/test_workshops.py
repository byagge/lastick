#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.operations.workshops.models import Workshop
from apps.users.models import User

def test_workshops():
    print("=== Тестирование цехов ===")
    
    # Проверяем количество цехов
    workshops = Workshop.objects.all()
    print(f"Всего цехов: {workshops.count()}")
    
    # Проверяем активные цеха
    active_workshops = Workshop.objects.filter(is_active=True)
    print(f"Активных цехов: {active_workshops.count()}")
    
    # Выводим информацию о каждом цехе
    for workshop in active_workshops:
        print(f"\nЦех: {workshop.name}")
        print(f"  Описание: {workshop.description}")
        print(f"  Менеджер: {workshop.manager.get_full_name() if workshop.manager else 'Не назначен'}")
        print(f"  Сотрудников: {workshop.users.count()}")
        print(f"  Дополнительных мастеров: {workshop.workshop_masters.count()}")
        
        # Проверяем мастеров
        for wm in workshop.workshop_masters.all():
            print(f"    - {wm.master.get_full_name()} (добавлен: {wm.added_at})")

def create_test_workshops():
    print("\n=== Создание тестовых цехов ===")
    
    WORKSHOPS = [
        'Распиловка',
        'Распил стекла',
        'Обработка на станках с ЧПУ',
        'Заготовительные работы',
        'Прессовое отделение',
        'Облицовка кромок',
        'Шлифовка (аппаратная)',
        'Шлифовка (сухая)',
        'Грунтование',
        'Шлифовка (белая)',
        'Окрасочное отделение',
        'Упаковка готовой продукции',
    ]
    
    created_count = 0
    for name in WORKSHOPS:
        workshop, created = Workshop.objects.get_or_create(
            name=name,
            defaults={
                'description': f'Цех {name}',
                'is_active': True
            }
        )
        if created:
            created_count += 1
            print(f'Создан цех: {name}')
        else:
            print(f'Цех уже существует: {name}')
    
    print(f'Успешно создано {created_count} новых цехов из {len(WORKSHOPS)}')

if __name__ == '__main__':
    try:
        create_test_workshops()
        test_workshops()
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc() 