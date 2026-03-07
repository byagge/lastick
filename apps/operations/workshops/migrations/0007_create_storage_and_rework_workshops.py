from django.db import migrations


def create_storage_and_rework_workshops(apps, schema_editor):
    Workshop = apps.get_model("operations_workshops", "Workshop")

    # ID3 — Склад
    storage, created_storage = Workshop.objects.get_or_create(
        pk=3,
        defaults={
            "name": "Склад",
            "description": "Складской цех (ID3): складская зона и сотрудники склада",
            "is_active": True,
        },
    )
    if not created_storage:
        # Обновляем имя/описание, если цех уже существует с другим названием
        changed = False
        if storage.name != "Склад":
            storage.name = "Склад"
            changed = True
        descr = "Складской цех (ID3): складская зона и сотрудники склада"
        if storage.description != descr:
            storage.description = descr
            changed = True
        if not storage.is_active:
            storage.is_active = True
            changed = True
        if changed:
            storage.save(update_fields=["name", "description", "is_active"])

    # ID4 — Обрабатывающий цех
    rework, created_rework = Workshop.objects.get_or_create(
        pk=4,
        defaults={
            "name": "Обрабатывающий цех",
            "description": "Обрабатывающий цех (ID4): переработка брака в сырьё",
            "is_active": True,
        },
    )
    if not created_rework:
        changed = False
        if rework.name != "Обрабатывающий цех":
            rework.name = "Обрабатывающий цех"
            changed = True
        descr = "Обрабатывающий цех (ID4): переработка брака в сырьё"
        if rework.description != descr:
            rework.description = descr
            changed = True
        if not rework.is_active:
            rework.is_active = True
            changed = True
        if changed:
            rework.save(update_fields=["name", "description", "is_active"])


def reverse_storage_and_rework_workshops(apps, schema_editor):
    Workshop = apps.get_model("operations_workshops", "Workshop")
    Workshop.objects.filter(
        pk__in=[3, 4],
        name__in=["Склад", "Обрабатывающий цех"],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("operations_workshops", "0006_workshoplog"),
    ]

    operations = [
        migrations.RunPython(
            create_storage_and_rework_workshops,
            reverse_storage_and_rework_workshops,
        ),
    ]


