from django.shortcuts import render
from billing.models import Sale, DailySale, SaleItem
from products.models import Product
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from datetime import date, timedelta
from django.db.models.functions import TruncDate, TruncMonth
import json
from django.utils.timezone import now
from datetime import timedelta
from accounts.decorators import admin_required
from django.utils import timezone
from django.db.models import Count
from customers.models import Customer
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required

@admin_required
def home(request):
    view_type = request.GET.get('view', 'monthly')
    today = date.today()

    # ---------------------
    # 📈 Sales Over Time Chart (from Sale model)
    # ---------------------
    if view_type == 'daily':
        sales = Sale.objects.annotate(day=TruncDate('date'))\
            .values('day')\
            .annotate(total=Sum('total_amount'))\
            .order_by('day')
        labels = [entry['day'].strftime('%Y-%m-%d') for entry in sales]
        data = [float(entry['total']) for entry in sales]
        label_text = "Daily Sales"
    else:  # Monthly
        sales = Sale.objects.extra(select={'month': "strftime('%%Y-%%m', date)"})\
            .values('month')\
            .annotate(total=Sum('total_amount'))\
            .order_by('month')
        labels = [entry['month'] for entry in sales]
        data = [float(entry['total']) for entry in sales]
        label_text = "Monthly Sales"

    # ---------------------
    # 💰 Today's Revenue (from DailySale)
    # ---------------------
    today_sale = DailySale.objects.filter(date=today).first()
    today_revenue = float(today_sale.total_amount) if today_sale else 0

    # ---------------------
    # 📊 Revenue Last 7 Days (from DailySale)
    # ---------------------
    last_7_days = DailySale.objects.filter(date__gte=today - timedelta(days=6)).order_by('date')
    history_labels = [entry.date.strftime('%Y-%m-%d') for entry in last_7_days]
    history_data = [float(entry.total_amount) for entry in last_7_days]

    low_stock_products = Product.objects.filter(stock_quantity__lt=F('low_stock_threshold'))

    # Slow-moving logic
    days_threshold = int(request.GET.get('slow_days', 30))  # default = 30 days
    cutoff_date = now().date() - timedelta(days=days_threshold)

    # Get IDs of products that have been sold in the last X days
    recently_sold_product_ids = Sale.objects.filter(date__gte=cutoff_date).values_list('items__id', flat=True).distinct()

    # Products NOT sold in X days
    slow_days_options = [7, 15, 30, 60, 90]
    slow_moving_products = Product.objects.exclude(saleitem__in=recently_sold_product_ids)

    # --- KPIs --- 
    total_earnings = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = Sale.objects.count()
    total_customers = Customer.objects.count()

    # --- Recent Sales Data (e.g., last 7 days for a chart) ---
    seven_days_ago = timezone.now().date() - timedelta(days=7)
    daily_sales_data = DailySale.objects.filter(date__gte=seven_days_ago).order_by('date')
    
    sales_chart_labels = [d.date.strftime('%Y-%m-%d') for d in daily_sales_data]
    sales_chart_data = [float(d.total_amount) for d in daily_sales_data]

    # --- Top Selling Products (e.g., Top 5 by quantity) ---
    top_products_data = Sale.objects.values(
        'items__product__name', 
        'items__product__selling_price', 
        # Add 'items__product__image_url' if you have an image field on your Product model
    ).annotate(
        total_quantity_sold=Sum('items__quantity')
    ).order_by('-total_quantity_sold')[:5] # Get top 5

    return render(request, 'home.html', {
        'labels': json.dumps(labels),
        'data': json.dumps(data),
        'label_text': label_text,
        'today_revenue': today_revenue,
        'history_labels': json.dumps(history_labels),
        'history_data': json.dumps(history_data),
        'low_stock_products': low_stock_products,
        'slow_moving_products': slow_moving_products,
        'days_threshold': days_threshold,
        'slow_days_options': slow_days_options,
        'total_earnings': total_earnings,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'earnings_change': 1.56, 
        'orders_change': -0.52, # Example negative change
        'customers_change': 2.10,
        'sales_chart_labels_json': json.dumps(sales_chart_labels),
        'sales_chart_data_json': json.dumps(sales_chart_data),
        'top_products': top_products_data,
    })

# Helper to safely serialize data for JS
def safe_serialize(data):
    return json.dumps(data, cls=DjangoJSONEncoder)

@login_required
def dashboard_view(request):
    """View for the main dashboard page, displaying KPIs and charts."""
    today = timezone.now().date()
    seven_days_ago = today - timedelta(days=7)
    twelve_months_ago = today - timedelta(days=365)
    
    # --- KPIs (Overall) --- 
    total_earnings = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = Sale.objects.count()
    total_customers = Customer.objects.count()

    # --- Calculate COGS & Net Profit (Overall) --- 
    total_cogs_expression = ExpressionWrapper(
        F('quantity') * F('product__cost_price'),
        output_field=DecimalField()
    )
    cogs_data = SaleItem.objects.aggregate(total_cogs=Sum(total_cogs_expression))
    total_cogs = cogs_data['total_cogs'] or 0
    net_profit = total_earnings - total_cogs

    # --- Recent Daily Sales Data (Last 7 Days) ---
    daily_sales_qs = DailySale.objects.filter(date__gte=seven_days_ago).order_by('date')
    daily_revenue_dict = {item.date: float(item.total_amount) for item in daily_sales_qs}
    daily_sales_chart_labels = []
    daily_sales_chart_data = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        daily_sales_chart_labels.append(day.strftime('%b %d'))
        daily_sales_chart_data.append(daily_revenue_dict.get(day, 0))
        
    # --- Daily Order Counts (Last 7 days) ---
    daily_orders_qs = Sale.objects.filter(date__gte=seven_days_ago)\
                                .annotate(day=TruncDate('date'))\
                                .values('day')\
                                .annotate(daily_count=Count('id'))\
                                .order_by('day')
    daily_orders_dict = {item['day']: item['daily_count'] for item in daily_orders_qs}
    daily_orders_chart_data = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        daily_orders_chart_data.append(daily_orders_dict.get(day, 0))

    # --- Monthly Revenue & Order Data (Last 12 Months) ---
    monthly_data_qs = Sale.objects.filter(date__gte=twelve_months_ago)\
                                .annotate(month=TruncMonth('date'))\
                                .values('month')\
                                .annotate(
                                    monthly_revenue=Sum('total_amount'), 
                                    monthly_orders=Count('id')
                                 )\
                                .order_by('month')
                                
    monthly_revenue_chart_labels = [m['month'].strftime('%Y-%m') for m in monthly_data_qs]
    monthly_revenue_chart_data = [float(m['monthly_revenue']) for m in monthly_data_qs]
    monthly_orders_chart_data = [m['monthly_orders'] for m in monthly_data_qs] # Use for potential future chart
    
    # Calculate totals for the period shown in the chart
    total_revenue_period = sum(monthly_revenue_chart_data)
    total_orders_period = sum(monthly_orders_chart_data)

    # --- Sales by Category (Overall) ---
    category_sales_qs = SaleItem.objects.values(
                            category_name=F('product__category__name')
                        ).annotate(
                            total_value=Sum(F('quantity') * F('price'))
                        ).order_by('-total_value')
    category_sales_chart_labels = [item['category_name'] for item in category_sales_qs if item['category_name']]
    category_sales_chart_data = [float(item['total_value']) for item in category_sales_qs if item['category_name']]

    # --- Top Selling Products (e.g., Top 5 by quantity) ---
    top_products_data = SaleItem.objects.values(
        product_name=F('product__name'), 
        product_price=F('product__selling_price'),
    ).annotate(
        total_quantity_sold=Sum('quantity')
    ).order_by('-total_quantity_sold')[:5]

    context = {
        # KPIs
        'total_earnings': total_earnings,
        'total_orders': total_orders,
        'total_customers': total_customers,
        'net_profit': net_profit,
        # % Changes (Placeholders)
        'earnings_change': 1.56, 
        'orders_change': -0.52, 
        'customers_change': 2.10,
        'net_profit_change': 0.85,
        'revenue_period_change': 0.56, # Placeholder
        'orders_period_change': 0.45, # Placeholder
        
        # Chart Data (Serialized JSON)
        'daily_sales_chart_labels_json': safe_serialize(daily_sales_chart_labels),
        'daily_sales_chart_data_json': safe_serialize(daily_sales_chart_data),
        'daily_orders_chart_data_json': safe_serialize(daily_orders_chart_data),
        'monthly_sales_chart_labels_json': safe_serialize(monthly_revenue_chart_labels),
        'monthly_sales_chart_data_json': safe_serialize(monthly_revenue_chart_data),
        'category_sales_chart_labels_json': safe_serialize(category_sales_chart_labels),
        'category_sales_chart_data_json': safe_serialize(category_sales_chart_data),
        
        # Other Data
        'total_revenue_period': total_revenue_period, # Renamed from total_monthly_revenue_period
        'total_orders_period': total_orders_period, # Added total orders for the period
        'top_products': top_products_data,
    }
    return render(request, 'dashboard/index.html', context)
