from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='EmployeeDocument',
        ),
    ]
