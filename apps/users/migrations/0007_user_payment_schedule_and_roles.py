from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_user_options_user_balance_alter_user_role'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='passport_number',
        ),
        migrations.RemoveField(
            model_name='user',
            name='inn',
        ),
        migrations.RemoveField(
            model_name='user',
            name='employment_date',
        ),
        migrations.RemoveField(
            model_name='user',
            name='fired_date',
        ),
        migrations.RemoveField(
            model_name='user',
            name='contract_number',
        ),
        migrations.AddField(
            model_name='user',
            name='payment_type',
            field=models.CharField(choices=[('fixed', '?????????????'), ('variable', '?????????')], default='fixed', max_length=10, verbose_name='??? ??????'),
        ),
        migrations.AddField(
            model_name='user',
            name='work_schedule',
            field=models.CharField(choices=[('day', '??????? (8-20)'), ('night', '?????? (20-8)')], default='day', max_length=10, verbose_name='??????'),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('admin', '?????????????'), ('accountant', '?????????'), ('worker', '?????????')], default='worker', max_length=20, verbose_name='????'),
        ),
    ]
