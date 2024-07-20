import os
import time
from dotenv import load_dotenv, find_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, RequestArgs
from py_clob_client.signer import Signer
from py_clob_client.constants import POLYGON
import requests
from headers import create_level_1_headers, create_level_2_headers
from datetime import datetime

def process_market_data(market_data):
    processed_markets = []
    for market in market_data:
        processed_market = {
            "question": market.get("question", "N/A"),
            "market_slug": market.get("market_slug", "N/A"),
            "status": "Active" if market.get("active", False) else "Inactive",
            "end_date": datetime.fromisoformat(market.get("end_date_iso", "").replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S") if market.get("end_date_iso") else "N/A",
            "description": market.get("description", "")[:100] + "..." if market.get("description", "") else "N/A",
            "outcomes": [
                {
                    "outcome": token.get("outcome", "N/A"),
                    "price": token.get("price", 0),
                    "winner": "Winner" if token.get("winner", False) else "Not winner"
                }
                for token in market.get("tokens", []) if token.get("outcome")
            ],
            "tags": market.get("tags", []) if isinstance(market.get("tags"), list) else []
        }
        processed_markets.append(processed_market)
    return processed_markets

def display_markets(processed_markets):
    for i, market in enumerate(processed_markets, 1):
        print(f"\n--- Market {i} ---")
        print(f"Question: {market['question']}")
        print(f"Slug: {market['market_slug']}")
        print(f"Status: {market['status']}")
        print(f"End Date: {market['end_date']}")
        print(f"Description: {market['description']}")
        print("Outcomes:")
        for outcome in market['outcomes']:
            print(f"  - {outcome['outcome']}: Price = {outcome['price']}, {outcome['winner']}")
        
        tags = market['tags']
        if isinstance(tags, list):
            print(f"Tags: {', '.join(tags)}")
        else:
            print(f"Tags: {tags}")

def main():
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
        # Example: Retrieve markets information
        request_args = RequestArgs(
            method="GET",
            request_path="/markets",
            body="",
        )
        
        # Create Level 2 headers for the markets request
        headers = create_level_2_headers(signer, api_creds, request_args)
        
        # Make the API request to retrieve markets
        endpoint = f"{host}/markets"
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        
        response_data = response.json()
        
        print(f"Keys in the response: {response_data.keys()}")
        
        if 'data' in response_data:
            market_data = response_data['data']
            print(f"Number of markets retrieved: {len(market_data)}")
            
            processed_markets = process_market_data(market_data)
            display_markets(processed_markets)
            
            # Print pagination info
            print(f"\nPagination Info:")
            print(f"Next Cursor: {response_data.get('next_cursor', 'N/A')}")
            print(f"Limit: {response_data.get('limit', 'N/A')}")
            print(f"Count: {response_data.get('count', 'N/A')}")
        else:
            print("No 'data' key found in the API response.")
            print(f"Full response content: {response_data}")
        
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {e}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()