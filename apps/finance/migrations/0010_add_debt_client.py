from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0003_client_whatsapp'),
        ('finance', '0009_add_preparation_specs_to_requestitem'),
    ]

    operations = [
        migrations.AddField(
            model_name='debt',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='debts', to='clients.client', verbose_name='Клиент'),
        ),
    ]
