from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0006_attendancesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='attendancerecord',
            name='penalty_charged_amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='Сумма уже списанного штрафа'),
        ),
    ]

