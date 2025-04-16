# Generated by Django 5.2 on 2025-04-16 13:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalFactor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Sales',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('quantity', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='ForecastConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('seasonality_mode', models.CharField(choices=[('additive', 'Additive'), ('multiplicative', 'Multiplicative')], default='multiplicative', max_length=20)),
                ('include_holidays', models.BooleanField(default=True)),
                ('forecast_horizon', models.PositiveIntegerField(default=30)),
                ('change_point_prior_scale', models.FloatField(default=0.05)),
                ('seasonality_prior_scale', models.FloatField(default=10.0)),
                ('holidays_prior_scale', models.FloatField(default=10.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='forecast_configs', to='products.product')),
            ],
        ),
        migrations.CreateModel(
            name='ExternalFactorValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('value', models.FloatField()),
                ('factor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='forecasting.externalfactor')),
            ],
            options={
                'unique_together': {('factor', 'date')},
            },
        ),
        migrations.CreateModel(
            name='ProductForecast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('predicted_demand', models.PositiveIntegerField()),
                ('lower_bound', models.PositiveIntegerField()),
                ('upper_bound', models.PositiveIntegerField()),
                ('confidence', models.FloatField(default=0.95)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='forecasts', to='products.product')),
            ],
            options={
                'ordering': ['product', 'date'],
                'unique_together': {('product', 'date')},
            },
        ),
    ]
