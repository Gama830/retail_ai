# Generated by Django 5.2 on 2025-04-09 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='last_purchase_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
