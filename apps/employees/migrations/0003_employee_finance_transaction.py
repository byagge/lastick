from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0013_remove_user_pay_category_user_credit_user_full_name_and_more'),
        ('employees', '0002_remove_employee_document'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmployeeFinanceTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('salary', 'Выплата зарплаты'), ('penalty', 'Штраф'), ('earning', 'Заработок')], max_length=20, verbose_name='Тип операции')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Сумма')),
                ('note', models.TextField(blank=True, verbose_name='Примечание')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата операции')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_transactions', to='users.user', verbose_name='Сотрудник')),
                ('issued_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_finance_transactions', to='users.user', verbose_name='Кто выдал')),
            ],
            options={
                'verbose_name': 'Финансовая операция сотрудника',
                'verbose_name_plural': 'Финансовые операции сотрудников',
                'ordering': ['-created_at'],
            },
        ),
    ]
