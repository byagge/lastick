from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_costing_labor_settings'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.CharField(blank=True, max_length=100, verbose_name='Размер')),
                ('color', models.CharField(blank=True, max_length=100, verbose_name='Цвет')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='products.product', verbose_name='Продукт')),
            ],
            options={
                'verbose_name': 'Позиция продукта',
                'verbose_name_plural': 'Позиции продукта',
                'ordering': ['id'],
            },
        ),
    ]
