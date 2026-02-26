from django.db import migrations


def create_initial_workshops(apps, schema_editor):
    Workshop = apps.get_model('operations_workshops', 'Workshop')

    # Создаём экструзионный цех, если его ещё нет
    Workshop.objects.get_or_create(
        name='Экструзионный цех',
        defaults={
            'description': 'Первый цех (экструзия), работает с сырьём и формирует полуфабрикат в нейтральную зону',
            'is_active': True,
        },
    )

    # Создаём пакетоотделочный / упаковочный цех, если его ещё нет
    Workshop.objects.get_or_create(
        name='Пакетоотделочный цех',
        defaults={
            'description': 'Второй цех (пакетоотделочный/упаковка), дорабатывает полуфабрикат и отправляет на склад готовой продукции',
            'is_active': True,
        },
    )


def reverse_initial_workshops(apps, schema_editor):
    Workshop = apps.get_model('operations_workshops', 'Workshop')
    Workshop.objects.filter(name__in=['Экструзионный цех', 'Пакетоотделочный цех']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('operations_workshops', '0003_alter_workshop_manager_alter_workshopmaster_master'),
    ]

    operations = [
        migrations.RunPython(create_initial_workshops, reverse_initial_workshops),
    ]


