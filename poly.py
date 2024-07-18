import os
import time
from dotenv import load_dotenv, find_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, RequestArgs
from py_clob_client.signing.hmac import build_hmac_signature
from py_clob_client.signer import Signer
from py_clob_client.signing.eip712 import sign_clob_auth_message
import requests
from headers import create_level_1_headers, create_level_2_headers

from py_clob_client.constants import POLYGON

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
    
    chain_id = POLYGON
    client = ClobClient(host, key=key, chain_id=chain_id)
    
    # Prepare headers
    signing_address = os.getenv("POLY_ADDRESS")
    nonce = "1"  # Default nonce value

    # Create Level 1 headers using the function from the library
    signer = Signer(key, chain_id=chain_id)
    headers = create_level_1_headers(signer, nonce=int(nonce))

    try:
        # Example of making a POST request with headers using requests library
        #endpoint = f"{host}/auth/derive-api-key"
        #response = requests.get(endpoint, headers=headers)
        #response.raise_for_status()  # Raise error for bad status codes

        #api_creds = client.derive_api_key()
        #print(f"API Key derived successfully: {api_creds}")

        # Store the API key, secret, and passphrase securely. Since the keys are derived these may be redundant
        api_key = os.getenv("API_KEY") # New line added for L2
        api_secret = os.getenv("API_SECRET")  # New line added for L2
        api_passphrase = os.getenv("API_PASSPHRASE")  # New line added for L2

        if not api_key or not api_secret or not api_passphrase:
            raise ValueError("API credentials not found in environment variables. Please check your .env file.")

        api_creds = ApiCreds(api_key=api_key, api_secret=api_secret, api_passphrase=api_passphrase)

        # Example of making an L2 authenticated request to retrieve API keys
        request_args = RequestArgs(  # New line added for L2
            method="GET",
            request_path="/auth/api-keys",
            body="",
        )
        
        # Create Level 2 headers
        headers = create_level_2_headers(signer, api_creds, request_args)  # New line added for L2

        # Make the API request
        endpoint = f"{host}/auth/api-keys"  # New line added for L2
        response = requests.get(endpoint, headers=headers)  # New line added for L2
        response.raise_for_status()  # New line added for L2

        api_keys = response.json()  # New line added for L2
        print(f"Retrieved API keys: {api_keys}")  # New line added for L2

        #potentially add some thing here for deleting
        #delete_response = client.delete_api_key()
        #print(f"API Key deleted: {delete_response}")

    except requests.exceptions.RequestException as e:
        print(f"Request Exception: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

# The code above demonstrates how to use the PolyMarket API client to interact with the PolyMarket API. It includes examples of creating Level 1 and Level 2 headers for authenticated requests, deriving API keys, and making authenticated requests to retrieve API keys. The code also demonstrates error handling and exception handling for requests.

