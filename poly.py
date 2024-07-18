import os
import time
from dotenv import load_dotenv, find_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.constants import AMOY
from py_clob_client.clob_types import ApiCreds, RequestArgs
from py_clob_client.signing.hmac import build_hmac_signature
from py_clob_client.signer import Signer
from py_clob_client.signing.eip712 import sign_clob_auth_message
import requests
from headers import create_level_1_headers

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
    signing_address = os.getenv("POLY_ADDRESS")
    nonce = "0"  # Default nonce value

    # Create Level 1 headers using the function from the library
    signer = Signer(key, chain_id=chain_id)
    headers = create_level_1_headers(signer, nonce=int(nonce))

    try:
        # Example of making a POST request with headers using requests library
        endpoint = f"{host}/auth/api-key"
        response = requests.post(endpoint, headers=headers)
        response.raise_for_status()  # Raise error for bad status codes

        api_creds = response.json()
        print(f"API Key created successfully: {api_creds}")
    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()