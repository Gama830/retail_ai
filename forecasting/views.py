from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from collections import defaultdict # Added for grouping

from .models import ProductForecast
from .forecaster import generate_forecasts

# Create your views here.
# from django.http import HttpResponse # No longer needed


def index(request):
    if request.method == 'POST':
        if 'generate_forecast' in request.POST:
            try:
                messages.info(request, "Forecast generation started. This may take a few moments...")
                generate_forecasts() # Use default 30 periods
                messages.success(request, "Demand forecasts generated successfully!")
            except Exception as e:
                messages.error(request, f"An error occurred during forecast generation: {e}")
            # Redirect to the same page using GET to prevent re-posting on refresh
            return redirect(reverse('forecast-home'))

    # GET request or after POST redirect
    today = timezone.now().date()
    # Fetch forecasts for today onwards, ordered by product then date
    forecasts_qs = ProductForecast.objects.filter(date__gte=today).select_related('product').order_by('product__name', 'date')
    
    # Group forecasts by product for easier template processing
    forecasts_by_product = defaultdict(list)
    for forecast in forecasts_qs:
        forecasts_by_product[forecast.product].append(forecast)
    
    # Convert defaultdict to regular dict for template safety
    context = {
        'forecasts_by_product': dict(forecasts_by_product),
    }
    return render(request, 'forecasting/index.html', context)