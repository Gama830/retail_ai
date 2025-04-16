# forecasting/models.py
from django.db import models
from products.models import Product  # Adjust this import based on your product model location

class Sales(models.Model):
    date = models.DateField()
    quantity = models.IntegerField()

class ExternalFactor(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

class ExternalFactorValue(models.Model):
    factor = models.ForeignKey(ExternalFactor, on_delete=models.CASCADE, related_name='values')
    date = models.DateField()
    value = models.FloatField()
    
    class Meta:
        unique_together = ['factor', 'date']

class ProductForecast(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='forecasts')
    date = models.DateField()
    predicted_demand = models.PositiveIntegerField()
    lower_bound = models.PositiveIntegerField()
    upper_bound = models.PositiveIntegerField()
    confidence = models.FloatField(default=0.95)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['product', 'date']
        ordering = ['product', 'date']

class ForecastConfig(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='forecast_configs')
    seasonality_mode = models.CharField(max_length=20, default='multiplicative', 
                                      choices=[('additive', 'Additive'), 
                                              ('multiplicative', 'Multiplicative')])
    include_holidays = models.BooleanField(default=True)
    forecast_horizon = models.PositiveIntegerField(default=30)
    change_point_prior_scale = models.FloatField(default=0.05)
    seasonality_prior_scale = models.FloatField(default=10.0)
    holidays_prior_scale = models.FloatField(default=10.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)