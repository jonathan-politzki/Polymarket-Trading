import requests

# Set the API endpoint URL
url = "https://api.polymarket.com/v1/markets"

# Set the query parameters
params = {
    "limit": 10,  # Adjust the limit as needed
    "offset": 0   # Adjust the offset as needed
}

# Set the headers (replace 'YOUR_API_KEY' with your actual API key)
headers = {
    "Accept": "application/json",
    "X-API-KEY": "YOUR_API_KEY"
}

# Make the API request
response = requests.get(url, params=params, headers=headers)

# Check if the request was successful
if response.status_code == 200:
    # Parse the JSON response
    data = response.json()
    
    # Access the market data
    markets = data["markets"]
    
    # Process the market data
    for market in markets:
        market_id = market["id"]
        market_question = market["question"]
        market_url = market["url"]
        # ... access other market details as needed
        
        print(f"Market ID: {market_id}")
        print(f"Question: {market_question}")
        print(f"URL: {market_url}")
        print("---")
else:
    print(f"Error: {response.status_code}")