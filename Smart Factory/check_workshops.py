#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.operations.workshops.models import Workshop

print("=== Все цеха в системе ===")

workshops = Workshop.objects.all().order_by('id')
for workshop in workshops:
    print(f"ID {workshop.id}: {workshop.name}")

print("\n=== Поиск цеха заготовки ===")
# Ищем цех с названием содержащим "заготовк"
prep_workshops = Workshop.objects.filter(name__icontains='заготовк')
print(f"Цеха с 'заготовк' в названии: {prep_workshops.count()}")
for workshop in prep_workshops:
    print(f"ID {workshop.id}: {workshop.name}")

# Ищем цех с названием содержащим "пресс"
press_workshops = Workshop.objects.filter(name__icontains='пресс')
print(f"Цеха с 'пресс' в названии: {press_workshops.count()}")
for workshop in press_workshops:
    print(f"ID {workshop.id}: {workshop.name}")
