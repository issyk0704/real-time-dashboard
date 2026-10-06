import os

import requests
from fastapi import FastAPI

app = FastAPI()

# API keys come from environment variables so they are never committed
STOCK_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
STOCK_API_URL = "https://www.alphavantage.co/query"
LIVECOINWATCH_API_URL = "https://api.livecoinwatch.com/coins/single"
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY", "")
REQUEST_TIMEOUT_SECONDS = 10


@app.get("/")
def read_root():
    return {"message": "Welcome to the Real-Time Dashboard API"}


# Plain `def` (not `async def`): requests is blocking, so FastAPI runs these in a threadpool
@app.get("/stocks/{symbol}")
def get_stock_price(symbol: str):
    try:
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": STOCK_API_KEY}
        response = requests.get(STOCK_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS).json()
        print("Stock API Response:", response)  # Log the full response

        # Extract stock price
        if response.get("Global Quote"):
            return {
                "symbol": symbol,
                "price": response["Global Quote"].get("05. price")
            }
        return {"error": "Stock data not found"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Failed to fetch stock data"}


@app.get("/crypto/{symbol}")
def get_crypto_price(symbol: str):
    try:
        # Headers and payload for Live Coin Watch API
        headers = {
            "x-api-key": LIVECOINWATCH_API_KEY
        }
        payload = {
            "currency": "USD",
            "code": symbol.upper(),  # Convert symbol to uppercase
            "meta": True
        }
        response = requests.post(
            LIVECOINWATCH_API_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        ).json()
        print("Crypto API Response:", response)  # Log the full response

        # Extract cryptocurrency price (the API returns no "code" field, so echo the request's)
        if response and "rate" in response:
            return {
                "symbol": symbol.upper(),
                "price": response.get("rate")
            }
        return {"error": "Crypto data not found"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Failed to fetch crypto data"}
