from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('finished_goods', '0003_finishedgoodsale'),
    ]

    operations = [
        migrations.AddField(
            model_name='finishedgoodsale',
            name='quantity',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
