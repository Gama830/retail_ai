from prophet import Prophet
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_forecast(sales_data, forecast_days=7):
    """
    Generate sales forecast using Facebook Prophet
    
    Args:
        sales_data: List of dictionaries containing 'date' and 'total' keys
        forecast_days: Number of days to forecast into the future
    
    Returns:
        forecast_df: DataFrame containing forecast results
        or None if insufficient data
    """
    # Convert sales data to DataFrame
    df = pd.DataFrame(sales_data)
    
    # Check if we have enough data points
    if len(df) < 2:
        return None
        
    df.columns = ['ds', 'y']  # Prophet requires these column names
    
    # Create and fit the model
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=True,
        interval_width=0.95
    )
    model.fit(df)
    
    # Create future dates for forecasting
    future_dates = model.make_future_dataframe(periods=forecast_days)
    
    # Generate forecast
    forecast = model.predict(future_dates)
    
    return forecast