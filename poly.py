import os
import time
from dotenv import load_dotenv, find_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, RequestArgs
from py_clob_client.signer import Signer
from py_clob_client.constants import POLYGON
import requests
from headers import create_level_2_headers
from datetime import datetime
import pandas as pd

def process_market_data(market_data):
    processed_markets = []
    for market in market_data:
        processed_market = {
            "question": market.get("question", "N/A"),
            "market_slug": market.get("market_slug", "N/A"),
            "status": "Active" if market.get("active", False) else "Inactive",
            "end_date": datetime.fromisoformat(market.get("end_date_iso", "").replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S") if market.get("end_date_iso") else "N/A",
            "description": market.get("description", "")[:100] + "..." if market.get("description", "") else "N/A",
            "outcomes": ", ".join([f"{token.get('outcome', 'N/A')}: {token.get('price', 0)}" for token in market.get("tokens", []) if token.get("outcome")]),
            "tags": ", ".join(market.get("tags", [])) if isinstance(market.get("tags"), list) else ""
        }
        processed_markets.append(processed_market)
    return processed_markets

def get_market_data():
    # Load .env file
    dotenv_path = find_dotenv()
    if not dotenv_path:
        raise FileNotFoundError("No .env file found. Please ensure the .env file is in the correct directory.")
    load_dotenv(dotenv_path)

    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    chain_id = POLYGON
    
    # Initialize client and signer
    client = ClobClient(host, key=key, chain_id=chain_id)
    signer = Signer(key, chain_id=chain_id)
    
    # Prepare API credentials
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    api_passphrase = os.getenv("API_PASSPHRASE")
    
    if not api_key or not api_secret or not api_passphrase:
        raise ValueError("API credentials not found in environment variables. Please check your .env file.")
    
    api_creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)
    
    try:
        # Prepare request arguments
        request_args = RequestArgs(
            method="GET",
            request_path="/markets",
            body="",
        )
        
        # Create Level 2 headers for the markets request
        headers = create_level_2_headers(signer, api_creds, request_args)
        
        # Make the API request to retrieve markets
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

def main():
    processed_markets = get_market_data()
    
    if processed_markets:
        df = pd.DataFrame(processed_markets)
        
        # Create directory if it doesn't exist
        os.makedirs('poly_data', exist_ok=True)
        
        # Save to CSV
        csv_path = os.path.join('poly_data', 'market_data.csv')
        df.to_csv(csv_path, index=False)
        print(f"Market data saved to {csv_path}")
    else:
        print("Failed to retrieve market data.")

if __name__ == "__main__":
    main()