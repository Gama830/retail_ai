from django.shortcuts import render
from billing.models import Sale, DailySale, SaleItem
from products.models import Product
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek, TruncYear
import json
from django.utils.timezone import now
from datetime import timedelta, date
from accounts.decorators import admin_required
from django.utils import timezone
from customers.models import Customer
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth.decorators import login_required
import calendar

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
@admin_required
def dashboard_view(request):
    """View for the main dashboard page, displaying KPIs and charts based on selected periods."""
    today = timezone.now().date()
    
    # --- Get Period Selection --- 
    revenue_period = request.GET.get('revenue_period', 'yearly') # Default to yearly
    
    # --- Calculate Date Ranges & Grouping --- 
    years_lookback = 5 # Number of years for the yearly view
    weeks_lookback = 4 # Number of weeks for the weekly view (including current)
    group_by_func = TruncDate # Default
    iterate_by = 'day' # Default

    if revenue_period == 'weekly':
        # Weekly view: Show aggregated data for the last N weeks
        current_week_monday = today - timedelta(days=today.weekday())
        start_date = current_week_monday - timedelta(weeks=weeks_lookback - 1) 
        group_by_func = TruncDate # Fetch daily data for manual weekly aggregation
        date_format = 'Week of %b %d' # Label format
        num_labels = weeks_lookback
        iterate_by = 'week' # Iterate week by week
    elif revenue_period == 'monthly':
        # Monthly view: Group by month for the current year
        start_date = date(today.year, 1, 1) 
        group_by_func = TruncMonth 
        date_format = '%b %Y' # Format like Jan 2024
        num_labels = 12
        iterate_by = 'month'
    else: # Yearly (default)
        start_date = date(today.year - years_lookback + 1, 1, 1) 
        group_by_func = TruncYear 
        date_format = '%Y' # Format like 2023
        num_labels = years_lookback
        iterate_by = 'year'

    # --- KPIs (Overall) --- 
    total_earnings = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = Sale.objects.count()
    total_customers = Customer.objects.count()

    # --- COGS & Net Profit (Overall) --- 
    total_cogs_expression = ExpressionWrapper(
        F('quantity') * F('product__cost_price'),
        output_field=DecimalField()
    )
    cogs_data = SaleItem.objects.aggregate(total_cogs=Sum(total_cogs_expression))
    total_cogs = cogs_data['total_cogs'] or 0
    net_profit = total_earnings - total_cogs

    # --- Revenue Chart Data (Based on selected period) --- 
    # Fetch data based on the overall start date and appropriate grouping for the source data
    # For weekly aggregation, we still need daily source data
    source_group_by = TruncDate if iterate_by == 'week' else group_by_func
    period_sales_qs = Sale.objects.filter(date__gte=start_date)\
                                .annotate(period_group=source_group_by('date'))\
                                .values('period_group')\
                                .annotate(
                                    period_revenue=Sum('total_amount'), 
                                    period_orders=Count('id')
                                 )\
                                .order_by('period_group')
                                
    period_data_dict = {item['period_group']: item for item in period_sales_qs} 
    
    revenue_chart_labels = []
    revenue_chart_data = []
    order_chart_data = [] # For the revenue card summary
    
    # Generate all labels for the period and fill data based on iteration type
    if iterate_by == 'year': 
        revenue_chart_data = [0.0] * num_labels
        order_chart_data = [0] * num_labels
        for i in range(num_labels):
            year_date = date(start_date.year + i, 1, 1)
            revenue_chart_labels.append(year_date.strftime(date_format))
            for group_date, data in period_data_dict.items():
                if group_date.year == year_date.year:
                    revenue_chart_data[i] = float(data.get('period_revenue', 0) or 0)
                    order_chart_data[i] = data.get('period_orders', 0) or 0
                    break
    elif iterate_by == 'month':
        revenue_chart_data = [0.0] * 12 # Initialize with 12 zeros
        order_chart_data = [0] * 12
        for i in range(1, 13): # Iterate through months 1 to 12
            month_start = date(today.year, i, 1) 
            revenue_chart_labels.append(month_start.strftime(date_format)) 
            for group_date, data in period_data_dict.items():
                if group_date.year == month_start.year and group_date.month == month_start.month:
                    month_index = group_date.month - 1 # 0-based index
                    revenue_chart_data[month_index] = float(data.get('period_revenue', 0) or 0)
                    order_chart_data[month_index] = data.get('period_orders', 0) or 0
                    break # Found the data for this month
    else: # iterate_by == 'week' (New weekly aggregation logic)
        revenue_chart_data = [0.0] * num_labels
        order_chart_data = [0] * num_labels
        for i in range(num_labels): # Loop through the number of weeks
            week_start_date = start_date + timedelta(weeks=i)
            week_end_date = week_start_date + timedelta(days=6)
            # Ensure the end date doesn't go past today for the current week
            if week_end_date > today:
                week_end_date = today 
                
            label = week_start_date.strftime(date_format)
            revenue_chart_labels.append(label)
            
            # Sum data for the days within this week
            weekly_revenue_sum = 0.0
            weekly_orders_sum = 0
            current_day = week_start_date
            while current_day <= week_end_date:
                daily_data = period_data_dict.get(current_day)
                if daily_data:
                    weekly_revenue_sum += float(daily_data.get('period_revenue', 0) or 0)
                    weekly_orders_sum += daily_data.get('period_orders', 0) or 0
                current_day += timedelta(days=1)
            
            revenue_chart_data[i] = weekly_revenue_sum
            order_chart_data[i] = weekly_orders_sum
            
    # Calculate totals for the selected period shown in the chart summary
    total_revenue_period = sum(revenue_chart_data)
    total_orders_period = sum(order_chart_data)
    
    # --- Mini Chart Data (Still last 7 days) --- 
    seven_days_ago = today - timedelta(days=7)
    daily_sales_qs = DailySale.objects.filter(date__gte=seven_days_ago).order_by('date')
    daily_revenue_dict = {item.date: float(item.total_amount) for item in daily_sales_qs}
    daily_sales_chart_labels = []
    daily_sales_chart_data = []
    for i in range(7):
        day = seven_days_ago + timedelta(days=i)
        daily_sales_chart_labels.append(day.strftime('%b %d'))
        daily_sales_chart_data.append(daily_revenue_dict.get(day, 0))
        
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

    # --- Sales by Category (Overall) --- 
    category_sales_qs = SaleItem.objects.values(
                            category_name=F('product__category__name')
                        ).annotate(
                            total_value=Sum(F('quantity') * F('price'))
                        ).order_by('-total_value')
    category_sales_chart_labels = [item['category_name'] for item in category_sales_qs if item['category_name']]
    category_sales_chart_data = [float(item['total_value']) for item in category_sales_qs if item['category_name']]

    # --- Top Selling Products (Overall) --- 
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
        # % Changes (Placeholders - calculation needs previous period data)
        'earnings_change': 1.56, 
        'orders_change': -0.52, 
        'customers_change': 2.10,
        'net_profit_change': 0.85,
        'revenue_period_change': 0.56, # Placeholder
        'orders_period_change': 0.45, # Placeholder
        
        # Chart Data (Serialized JSON)
        # Mini charts still use last 7 days
        'daily_sales_chart_labels_json': safe_serialize(daily_sales_chart_labels),
        'daily_sales_chart_data_json': safe_serialize(daily_sales_chart_data),
        'daily_orders_chart_data_json': safe_serialize(daily_orders_chart_data),
        # Main revenue chart uses selected period
        'revenue_chart_labels_json': safe_serialize(revenue_chart_labels),
        'revenue_chart_data_json': safe_serialize(revenue_chart_data),
        # Category chart is overall
        'category_sales_chart_labels_json': safe_serialize(category_sales_chart_labels),
        'category_sales_chart_data_json': safe_serialize(category_sales_chart_data),
        
        # Other Data
        'total_revenue_period': total_revenue_period, # Sum for the selected period
        'total_orders_period': total_orders_period, # Sum for the selected period
        'top_products': top_products_data, # Overall top products
        'current_revenue_period': revenue_period, # Pass selected period back if needed
    }
    return render(request, 'dashboard/index.html', context)
