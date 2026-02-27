# Generated manually for simplified defect system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("defects", "0005_alter_defect_confirmed_by_and_more"),
        ("employee_tasks", "0008_employeetask_additional_penalties_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(model_name="defect", name="status"),
        migrations.RemoveField(model_name="defect", name="defect_type"),
        migrations.RemoveField(model_name="defect", name="confirmed_by"),
        migrations.RemoveField(model_name="defect", name="confirmed_at"),
        migrations.RemoveField(model_name="defect", name="target_workshop"),
        migrations.RemoveField(model_name="defect", name="transferred_at"),
        migrations.RemoveField(model_name="defect", name="is_repairable"),
        migrations.RemoveField(model_name="defect", name="repair_task"),
        migrations.RemoveField(model_name="defect", name="master_comment"),
        migrations.RemoveField(model_name="defect", name="repair_comment"),
        migrations.RemoveField(model_name="defect", name="penalty_applied"),
        migrations.AddField(
            model_name="defect",
            name="quantity",
            field=models.DecimalField(
                decimal_places=3,
                default=0,
                max_digits=12,
                verbose_name="Количество (кг)",
            ),
        ),
        migrations.AddField(
            model_name="defect",
            name="employee_comment",
            field=models.TextField(blank=True, verbose_name="Комментарий сотрудника"),
        ),
        migrations.AddField(
            model_name="defect",
            name="admin_comment",
            field=models.TextField(blank=True, verbose_name="Комментарий администратора"),
        ),
        migrations.AddField(
            model_name="defect",
            name="penalty_assigned_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_defect_penalties",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Штраф назначил",
            ),
        ),
        migrations.AddField(
            model_name="defect",
            name="penalty_assigned_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Дата назначения штрафа"
            ),
        ),
        migrations.AlterField(
            model_name="defect",
            name="penalty_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Сумма штрафа",
            ),
        ),
        migrations.AlterField(
            model_name="defect",
            name="product",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="defects",
                to="products.product",
                verbose_name="Продукт",
            ),
        ),
        migrations.AlterField(
            model_name="defect",
            name="employee_task",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="defects",
                to="employee_tasks.employeetask",
                verbose_name="Задание сотрудника",
            ),
        ),
        migrations.AlterField(
            model_name="defect",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="defects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Сотрудник",
            ),
        ),
    ]
