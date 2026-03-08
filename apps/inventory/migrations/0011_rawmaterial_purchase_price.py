from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("factory_inventory", "0010_materialissuelog"),
    ]

    operations = [
        migrations.AddField(
            model_name="rawmaterial",
            name="purchase_price",
            field=models.DecimalField(
                default=0,
                decimal_places=2,
                max_digits=10,
                verbose_name="Цена закупки (ср.)",
            ),
        ),
    ]
