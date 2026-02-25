#!/usr/bin/env python
"""
Скрипт для создания тестовых данных
"""
import os
import sys
import django
from datetime import date, timedelta
import random

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.users.models import User
from apps.operations.workshops.models import Workshop
from apps.employees.models import EmployeeStatistics, EmployeeTask, EmployeeNotification, EmployeeDocument

def create_test_data():
    print("Создание тестовых данных...")
    
    # Создаем цеха
    workshops = []
    workshop_names = ['Сборочный цех', 'Покрасочный цех', 'Упаковочный цех', 'Контроль качества']
    
    for name in workshop_names:
        workshop, created = Workshop.objects.get_or_create(
            name=name,
            defaults={
                'description': f'Описание для {name}',
                'is_active': True
            }
        )
        workshops.append(workshop)
        if created:
            print(f"Создан цех: {name}")
    
    # Создаем сотрудников
    employees_data = [
        {
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'role': User.Role.WORKER,
            'phone': '+996700123456',
            'email': 'ivanov@example.com',
            'workshop': workshops[0],
            'passport_number': '1234567890',
            'inn': '123456789012',
            'employment_date': date(2023, 1, 15),
            'contract_number': 'ТД-001'
        },
        {
            'first_name': 'Петр',
            'last_name': 'Петров',
            'role': User.Role.MASTER,
            'phone': '+996700123457',
            'email': 'petrov@example.com',
            'workshop': workshops[1],
            'passport_number': '1234567891',
            'inn': '123456789013',
            'employment_date': date(2022, 6, 10),
            'contract_number': 'ТД-002'
        },
        {
            'first_name': 'Анна',
            'last_name': 'Сидорова',
            'role': User.Role.WORKER,
            'phone': '+996700123458',
            'email': 'sidorova@example.com',
            'workshop': workshops[2],
            'passport_number': '1234567892',
            'inn': '123456789014',
            'employment_date': date(2023, 3, 20),
            'contract_number': 'ТД-003'
        },
        {
            'first_name': 'Мария',
            'last_name': 'Козлова',
            'role': User.Role.WORKER,
            'phone': '+996700123459',
            'email': 'kozlova@example.com',
            'workshop': workshops[3],
            'passport_number': '1234567893',
            'inn': '123456789015',
            'employment_date': date(2023, 2, 5),
            'contract_number': 'ТД-004'
        },
        {
            'first_name': 'Алексей',
            'last_name': 'Смирнов',
            'role': User.Role.WORKER,
            'phone': '+996700123460',
            'email': 'smirnov@example.com',
            'workshop': workshops[0],
            'passport_number': '1234567894',
            'inn': '123456789016',
            'employment_date': date(2023, 4, 12),
            'contract_number': 'ТД-005'
        }
    ]
    
    for emp_data in employees_data:
        # Создаем пользователя
        user, created = User.objects.get_or_create(
            email=emp_data['email'],
            defaults=emp_data
        )
        
        if created:
            # Устанавливаем пароль
            user.set_password('password123')
            user.save()
            print(f"Создан сотрудник: {user.get_full_name()}")
            
            # Создаем статистику
            stats, stats_created = EmployeeStatistics.objects.get_or_create(
                employee=user,
                defaults={
                    'completed_works': random.randint(20, 50),
                    'defects': random.randint(1, 10),
                    'monthly_salary': random.randint(40000, 80000),
                    'efficiency': random.randint(70, 95),
                    'avg_productivity': random.randint(5, 10),
                    'defect_rate': random.randint(5, 15),
                    'hours_worked': random.randint(160, 200),
                    'overtime_hours': random.randint(0, 20),
                    'quality_score': random.randint(7, 10),
                    'deadline_compliance': random.randint(80, 100),
                    'initiative_score': random.randint(7, 10),
                    'teamwork_score': random.randint(7, 10),
                    'productivity_chart': [random.randint(2, 8) for _ in range(7)],
                    'monthly_productivity': [random.randint(3, 10) for _ in range(30)],
                    'salary_history': [45000, 52000, 48000, 55000, 58000, 62000]
                }
            )
            
            if stats_created:
                print(f"Создана статистика для: {user.get_full_name()}")
            
            # Создаем задачи
            tasks = [
                'Проверить качество продукции',
                'Подготовить отчет о работе',
                'Провести инструктаж по технике безопасности',
                'Обновить документацию'
            ]
            
            for task_text in random.sample(tasks, random.randint(1, 3)):
                task, task_created = EmployeeTask.objects.get_or_create(
                    employee=user,
                    text=task_text,
                    defaults={'completed': random.choice([True, False])}
                )
                if task_created:
                    print(f"Создана задача для {user.get_full_name()}: {task_text}")
            
            # Создаем уведомления
            notifications = [
                {'title': 'Новое задание', 'text': 'Вам назначено новое задание на сегодня'},
                {'title': 'Обновление системы', 'text': 'Система будет обновлена в ближайшее время'},
                {'title': 'Собрание', 'text': 'Завтра в 10:00 состоится общее собрание'}
            ]
            
            for notif_data in random.sample(notifications, random.randint(1, 2)):
                notif, notif_created = EmployeeNotification.objects.get_or_create(
                    employee=user,
                    title=notif_data['title'],
                    defaults={'text': notif_data['text']}
                )
                if notif_created:
                    print(f"Создано уведомление для {user.get_full_name()}: {notif_data['title']}")
            
            # Создаем документы
            documents = [
                ('passport_main', 'uploaded'),
                ('employment_contract', 'uploaded'),
                ('work_book', 'uploaded'),
                ('medical_book', 'pending')
            ]
            
            for doc_type, status in documents:
                doc, doc_created = EmployeeDocument.objects.get_or_create(
                    employee=user,
                    document_type=doc_type,
                    defaults={'status': status}
                )
                if doc_created:
                    print(f"Создан документ для {user.get_full_name()}: {doc_type}")
    
    print("Тестовые данные созданы успешно!")
    print(f"Создано цехов: {len(workshops)}")
    print(f"Создано сотрудников: {len(employees_data)}")

if __name__ == '__main__':
    create_test_data() 