from dotenv import load_dotenv, find_dotenv
import os
import time
import requests
from py_clob_client.client import ClobClient
from py_clob_client.constants import AMOY
from py_clob_client.exceptions import PolyApiException

# Load .env file
dotenv_path = find_dotenv()
if not dotenv_path:
    raise FileNotFoundError("No .env file found. Please ensure the .env file is in the correct directory.")
else:
    print(f"Loading environment variables from: {dotenv_path}")
    load_dotenv(dotenv_path)

def main():
    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    
    if not key:
        raise ValueError("Private key not found in environment variables. Please check your .env file.")
    
    print(f"Loaded private key: {key[:5]}...")  # Print the first few characters for confirmation
    
    chain_id = AMOY
    client = ClobClient(host, key=key, chain_id=chain_id)

    # Prepare headers
    poly_address = os.getenv("POLY_ADDRESS")
    poly_signature = os.getenv("POLY_SIGNATURE")
    poly_timestamp = str(int(time.time()))  # Current UNIX timestamp
    poly_nonce = "0"  # Default nonce value

    headers = {
        "POLY_ADDRESS": poly_address,
        "POLY_SIGNATURE": poly_signature,
        "POLY_TIMESTAMP": poly_timestamp,
        "POLY_NONCE": poly_nonce
    }

    try:
        api_key = client.create_api_key(headers=headers)
        print(f"API Key created successfully: {api_key}")
    except PolyApiException as e:
        print(f"Poly API Exception: {e}")
        # Add more specific handling based on the exception details
    except Exception as e:
        print(f"Error: {e}")
        # Handle other unexpected exceptions here

if __name__ == "__main__":
    main()
