from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finished_goods', '0002_finishedgood_order_item_finishedgood_packaging_date_and_more'),
        ('clients', '0002_client_status'),
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FinishedGoodSale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('sold_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='finished_good_sales', to='clients.client')),
                ('finished_good', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sales', to='finished_goods.finishedgood')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finished_good_sales', to='orders.order')),
            ],
            options={
                'ordering': ['-sold_at'],
            },
        ),
    ]
