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
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_markets(client, signer, api_creds, host):
    all_markets = []
    next_cursor = ""
    
    while True:
        try:
            request_args = RequestArgs(
                method="GET",
                request_path=f"/markets?next_cursor={next_cursor}",
                body="",
            )
            
            headers = create_level_2_headers(signer, api_creds, request_args)
            
            endpoint = f"{host}{request_args.request_path}"
            response = requests.get(endpoint, headers=headers)
            response.raise_for_status()
            
            response_data = response.json()
            
            if 'data' in response_data:
                all_markets.extend(response_data['data'])
                logging.info(f"Retrieved {len(response_data['data'])} markets. Total: {len(all_markets)}")
                
                if response_data.get('next_cursor') == 'LTE=':
                    break
                next_cursor = response_data.get('next_cursor', "")
            else:
                logging.error("No 'data' key found in the API response.")
                break
            
            time.sleep(1)  # Add a delay to avoid hitting rate limits
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Request Exception: {e}")
            break
        except Exception as e:
            logging.error(f"Error: {e}")
            break
    
    return all_markets

def get_extended_timeseries_data(client, signer, api_creds, host, token_id):
    try:
        end_ts = int(time.time())
        start_ts = end_ts - (365 * 24 * 60 * 60)  # 1 year ago
        
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
            logging.warning(f"No 'history' key found in the API response for token {token_id}.")
            return None
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception for token {token_id}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error for token {token_id}: {e}")
        return None

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
        
        for i, token in enumerate(market.get("tokens", [])):
            processed_market[f"token_{i+1}_id"] = token.get("token_id", "N/A")
            processed_market[f"token_{i+1}_outcome"] = token.get("outcome", "N/A")
        
        processed_markets.append(processed_market)
    return processed_markets

def main():
    try:
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
        
        all_markets = get_all_markets(client, signer, api_creds, host)
        processed_markets = process_market_data(all_markets)
        
        if processed_markets:
            df = pd.DataFrame(processed_markets)
            
            os.makedirs('poly_data', exist_ok=True)
            
            csv_path = os.path.join('poly_data', 'extended_market_data.csv')
            df.to_csv(csv_path, index=False)
            logging.info(f"Extended market data saved to {csv_path}")
            
            # Collect extended timeseries data
            timeseries_data = []
            for _, row in tqdm(df.iterrows(), total=df.shape[0], desc="Collecting timeseries data"):
                for i in range(1, 3):  # Assuming there are always 2 tokens
                    token_id = row[f'token_{i}_id']
                    token_outcome = row[f'token_{i}_outcome']
                    history = get_extended_timeseries_data(client, signer, api_creds, host, token_id)
                    if history:
                        for point in history:
                            timeseries_data.append({
                                'token_id': token_id,
                                'token_outcome': token_outcome,
                                'market_slug': row['market_slug'],
                                'timestamp': datetime.fromtimestamp(point['t']).strftime('%Y-%m-%d %H:%M:%S'),
                                'price': point['p']
                            })
                    time.sleep(0.5)  # Add a small delay between requests
            
            timeseries_df = pd.DataFrame(timeseries_data)
            timeseries_csv_path = os.path.join('poly_data', 'extended_time_series_data.csv')
            timeseries_df.to_csv(timeseries_csv_path, index=False)
            logging.info(f"Extended time series data saved to {timeseries_csv_path}")

            # Merge market and timeseries data
            linked_data = merge_market_and_timeseries_data(df, timeseries_df)
            
            # Save the linked dataset
            linked_data_path = os.path.join('poly_data', 'extended_linked_market_timeseries_data.csv')
            linked_data.to_csv(linked_data_path, index=False)
            logging.info(f"Extended linked dataset saved to {linked_data_path}")

            logging.info(f"Total markets collected: {len(all_markets)}")
            logging.info(f"Total timeseries data points: {len(timeseries_data)}")
            logging.info("Data collection completed successfully.")
        else:
            logging.error("Failed to retrieve market data.")
    except Exception as e:
        logging.exception(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()