import pandas as pd
import numpy as np
from datetime import datetime

def add_features(df):
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Add day of week
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    
    # Add is_weekend
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Add hour of day
    df['hour_of_day'] = df['timestamp'].dt.hour
    
    # Calculate price momentum (percent change over last 24 hours)
    df['price_24h_ago'] = df.groupby('token_id')['price'].shift(24)
    df['momentum_24h'] = (df['price'] - df['price_24h_ago']) / df['price_24h_ago']
    
    # Calculate 7-day moving average
    df['ma_7d'] = df.groupby('token_id')['price'].rolling(window=168).mean().reset_index(0, drop=True)
    
    # Calculate distance from 7-day moving average
    df['distance_from_ma'] = (df['price'] - df['ma_7d']) / df['ma_7d']
    
    # Calculate days until market end
    df['days_until_end'] = (pd.to_datetime(df['end_date']) - df['timestamp']).dt.total_seconds() / (24 * 60 * 60)
    
    # Calculate price volatility (standard deviation over last 24 hours)
    df['volatility_24h'] = df.groupby('token_id')['price'].rolling(window=24).std().reset_index(0, drop=True)
    
    return df

# Load the linked dataset
linked_data = pd.read_csv('poly_data/extended_time_series_data.csv')

# Add features
enhanced_data = add_features(linked_data)

# Save the enhanced dataset
enhanced_data.to_csv('poly_data/cleaned_merged_data.csv', index=False)
print("Enhanced dataset saved to poly_data/cleaned_merged_data.csv")
