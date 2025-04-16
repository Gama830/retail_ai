import pandas as pd
from prophet import Prophet
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
import logging

from products.models import Product
from billing.models import SaleItem
from .models import ProductForecast

# Configure logging
logger = logging.getLogger(__name__)

def get_historical_sales_data():
    """Fetches and aggregates historical sales data by product and day."""
    logger.info("Fetching historical sales data...")
    
    sales_data = SaleItem.objects.annotate(
        sale_date=TruncDate('sale__date') # Truncate DateTimeField to DateField
    ).values(
        'product_id', 'sale_date'
    ).annotate(
        daily_quantity=Sum('quantity')
    ).order_by('product_id', 'sale_date')

    if not sales_data:
        logger.warning("No sales data found.")
        return pd.DataFrame()

    df = pd.DataFrame(list(sales_data))
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    logger.info(f"Successfully fetched and aggregated data for {df['product_id'].nunique()} products.")
    return df

def generate_forecasts(periods=30): # Default forecast for 30 days
    """Generates demand forecasts for all products and saves them."""
    logger.info(f"Starting forecast generation for {periods} periods.")
    
    all_sales_df = get_historical_sales_data()
    if all_sales_df.empty:
        logger.warning("Forecast generation skipped: No historical sales data.")
        return

    products = Product.objects.all()
    forecasts_to_create = []
    today = timezone.now().date()

    for product in products:
        logger.info(f"Processing product ID: {product.id} ({product.name})")
        product_sales = all_sales_df[all_sales_df['product_id'] == product.id].copy()

        if product_sales.empty or len(product_sales) < 2: # Prophet needs at least 2 data points
            logger.warning(f"Skipping product ID {product.id}: Insufficient data points ({len(product_sales)})." )
            continue
            
        # Prepare data for Prophet: columns 'ds' (datetime) and 'y' (value)
        product_sales.rename(columns={'sale_date': 'ds', 'daily_quantity': 'y'}, inplace=True)
        
        # Ensure 'ds' is timezone-naive if it's timezone-aware
        if pd.api.types.is_datetime64_any_dtype(product_sales['ds']) and product_sales['ds'].dt.tz is not None:
           product_sales['ds'] = product_sales['ds'].dt.tz_localize(None)

        try:
            # Initialize and train the Prophet model
            model = Prophet(daily_seasonality=False, weekly_seasonality=True, yearly_seasonality=True) # Adjust seasonality as needed
            model.fit(product_sales[['ds', 'y']])

            # Create future dataframe for predictions
            future = model.make_future_dataframe(periods=periods)

            # Generate forecast
            forecast = model.predict(future)

            # Filter for future dates and extract relevant columns
            forecast_results = forecast[forecast['ds'].dt.date >= today][['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

            # Prepare ProductForecast instances
            for _, row in forecast_results.iterrows():
                # Ensure predicted demand and bounds are non-negative integers
                predicted_demand = max(0, int(round(row['yhat'])))
                lower_bound = max(0, int(round(row['yhat_lower'])))
                upper_bound = max(0, int(round(row['yhat_upper'])))
                
                # Skip if predicted demand is zero and bounds are also zero (or negative after rounding)
                if predicted_demand == 0 and lower_bound == 0 and upper_bound == 0:
                    continue

                forecasts_to_create.append(
                    ProductForecast(
                        product=product,
                        date=row['ds'].date(),
                        predicted_demand=predicted_demand,
                        lower_bound=lower_bound,
                        upper_bound=upper_bound,
                        # confidence is implicitly ~95% by Prophet's default interval_width
                    )
                )
            logger.info(f"Generated forecast for product ID: {product.id}")

        except Exception as e:
            logger.error(f"Error forecasting product ID {product.id}: {e}", exc_info=True)
            continue # Move to the next product if an error occurs

    # Bulk create forecasts (more efficient)
    if forecasts_to_create:
        try:
            # Clear old forecasts before inserting new ones
            logger.info(f"Deleting existing forecasts...")
            ProductForecast.objects.all().delete() 
            
            logger.info(f"Bulk creating {len(forecasts_to_create)} new forecast records...")
            ProductForecast.objects.bulk_create(forecasts_to_create, ignore_conflicts=True) # ignore_conflicts might be useful if regeneration happens often
            logger.info("Successfully saved new forecasts.")
        except Exception as e:
             logger.error(f"Error bulk saving forecasts: {e}", exc_info=True)
    else:
        logger.warning("No forecasts were generated to save.")

    logger.info("Forecast generation process finished.") 