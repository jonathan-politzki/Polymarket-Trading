import logging
import os
import time
from dotenv import load_dotenv, find_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, RequestArgs
from py_clob_client.signer import Signer
from py_clob_client.constants import POLYGON
import requests
from headers import create_level_2_headers
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# NOTE: Set this to True to use API calls, False to use extended datasets
USE_API = False

def process_market_data(market_data):
    processed_markets = []
    for market in market_data:
        processed_market = {
            "question": market.get("question", "N/A"),
            "market_slug": market.get("market_slug", "N/A"),
            "status": "Active" if market.get("active", False) else "Inactive",
            "end_date": datetime.fromisoformat(market.get("end_date_iso", "").replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S") if market.get("end_date_iso") else "N/A",
            "description": market.get("description", "")[:100] + "..." if market.get("description", "") else "N/A",
            "tags": ", ".join(market.get("tags", [])) if isinstance(market.get("tags"), list) else ""
        }
        
        # Add token information
        for i, token in enumerate(market.get("tokens", [])):
            processed_market[f"token_{i+1}_id"] = token.get("token_id", "N/A")
            processed_market[f"token_{i+1}_outcome"] = token.get("outcome", "N/A")
        
        processed_markets.append(processed_market)
    return processed_markets

def get_market_data(client, signer, api_creds, host):
    try:
        request_args = RequestArgs(
            method="GET",
            request_path="/markets",
            body="",
        )
        
        headers = create_level_2_headers(signer, api_creds, request_args)
        
        endpoint = f"{host}{request_args.request_path}"
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        
        if 'data' in response_data:
            market_data = response_data['data']
            print(f"Number of markets retrieved: {len(market_data)}")
            processed_markets = process_market_data(market_data)
            return processed_markets
        else:
            print("No 'data' key found in the API response.")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_timeseries_data(client, signer, api_creds, host, token_id):
    try:
        end_ts = int(time.time())
        start_ts = end_ts - (30 * 24 * 60 * 60)  # 30 days ago
        
        request_args = RequestArgs(
            method="GET",
            request_path=f"/prices-history?market={token_id}&startTs={start_ts}&endTs={end_ts}&fidelity=60",
            body="",
        )
        
        headers = create_level_2_headers(signer, api_creds, request_args)
        
        endpoint = f"{host}{request_args.request_path}"
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        
        if 'history' in response_data:
            return response_data['history']
        else:
            print(f"No 'history' key found in the API response for token {token_id}.")
            return None
        
    except requests.exceptions.RequestException as e:
        print(f"Request Exception for token {token_id}: {e}")
        return None
    except Exception as e:
        print(f"Error for token {token_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def merge_market_and_timeseries_data(market_data, time_series_data):
    # Reset index to ensure we have a continuous range index
    market_data = market_data.reset_index(drop=True)
    
    # Melt the market data to create rows for each token
    market_data_melted = pd.melt(market_data, 
                                 id_vars=['question', 'market_slug', 'status', 'end_date', 'description', 'tags'],
                                 value_vars=['token_1_id', 'token_2_id'],
                                 var_name='token_number', 
                                 value_name='token_id')

    # Add the corresponding outcome for each token
    market_data_melted['token_outcome'] = market_data_melted.apply(
        lambda row: market_data.loc[row.name // 2, 'token_1_outcome'] if row['token_number'] == 'token_1_id' 
        else market_data.loc[row.name // 2, 'token_2_outcome'], axis=1
    )

    # Merge the melted market data with the time series data
    merged_data = pd.merge(time_series_data, market_data_melted, 
                           on=['token_id', 'token_outcome', 'market_slug'], 
                           how='left')

    # Sort the data by market_slug, token_id, and timestamp
    merged_data = merged_data.sort_values(['market_slug', 'token_id', 'timestamp'])

    return merged_data

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

def main():
    try:
        if USE_API:
            dotenv_path = find_dotenv()
            if not dotenv_path:
                raise FileNotFoundError("No .env file found. Please ensure the .env file is in the correct directory.")
            load_dotenv(dotenv_path)

            host = "https://clob.polymarket.com"
            key = os.getenv("PK")
            chain_id = POLYGON
            
            client = ClobClient(host, key=key, chain_id=chain_id)
            signer = Signer(key, chain_id=chain_id)
            
            api_key = os.getenv("API_KEY")
            api_secret = os.getenv("API_SECRET")
            api_passphrase = os.getenv("API_PASSPHRASE")
            
            if not api_key or not api_secret or not api_passphrase:
                raise ValueError("API credentials not found in environment variables. Please check your .env file.")
            
            api_creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)
            
            processed_markets = get_market_data(client, signer, api_creds, host)
            
            if processed_markets:
                df = pd.DataFrame(processed_markets)
                
                os.makedirs('poly_data', exist_ok=True)
                
                csv_path = os.path.join('poly_data', 'market_data.csv')
                df.to_csv(csv_path, index=False)
                logging.info(f"Market data saved to {csv_path}")
                
                # Collect timeseries data
                timeseries_data = []
                for _, row in df.iterrows():
                    for i in range(1, 3):  # Assuming there are always 2 tokens
                        token_id = row[f'token_{i}_id']
                        token_outcome = row[f'token_{i}_outcome']
                        history = get_timeseries_data(client, signer, api_creds, host, token_id)
                        if history:
                            for point in history:
                                timeseries_data.append({
                                    'token_id': token_id,
                                    'token_outcome': token_outcome,
                                    'market_slug': row['market_slug'],
                                    'timestamp': datetime.fromtimestamp(point['t']).strftime('%Y-%m-%d %H:%M:%S'),
                                    'price': point['p']
                                })
                
                timeseries_df = pd.DataFrame(timeseries_data)
                timeseries_csv_path = os.path.join('poly_data', 'time_series_data.csv')
                timeseries_df.to_csv(timeseries_csv_path, index=False)
                logging.info(f"Time series data saved to {timeseries_csv_path}")
            else:
                logging.error("Failed to retrieve market data.")
                return
        else:
            # Load the extended market data
            df = pd.read_csv('poly_data/extended_market_data.csv')
            logging.info(f"Loaded extended market data with {len(df)} rows")

            # Load the extended time series data
            timeseries_df = pd.read_csv('poly_data/extended_time_series_data.csv')
            logging.info(f"Loaded extended time series data with {len(timeseries_df)} rows")

        # Merge market and timeseries data
        linked_data = merge_market_and_timeseries_data(df, timeseries_df)
        logging.info(f"Merged data, resulting in {len(linked_data)} rows")

        # Add features
        enhanced_data = add_features(linked_data)
        logging.info("Added features to the merged dataset")

        # Save the enhanced dataset
        enhanced_data_path = os.path.join('poly_data', 'enhanced_linked_data.csv')
        enhanced_data.to_csv(enhanced_data_path, index=False)
        logging.info(f"Enhanced linked dataset saved to {enhanced_data_path}")

        # Display the first few rows and basic information about the enhanced dataset
        logging.info("First few rows of the enhanced dataset:")
        logging.info(enhanced_data.head())
        logging.info("Information about the enhanced dataset:")
        logging.info(enhanced_data.info())

    except Exception as e:
        logging.exception(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()