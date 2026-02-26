from django.db import migrations, models
import django.utils.timezone
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0003_fix_check_in_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendancerecord',
            name='date',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Дата'),
        ),
        migrations.AlterField(
            model_name='attendancerecord',
            name='penalty_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('100.00'), max_digits=10, verbose_name='Сумма штрафа'),
        ),
        migrations.AddField(
            model_name='attendancerecord',
            name='penalty_manual',
            field=models.BooleanField(default=False, verbose_name='Штраф задан вручную'),
        ),
    ]
