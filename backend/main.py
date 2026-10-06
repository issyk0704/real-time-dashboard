import os
import time
from pathlib import Path

import requests
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# API keys come from environment variables so they are never committed
STOCK_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
STOCK_API_URL = "https://www.alphavantage.co/query"
LIVECOINWATCH_API_URL = "https://api.livecoinwatch.com/coins/single"
LIVECOINWATCH_API_KEY = os.getenv("LIVECOINWATCH_API_KEY", "")
REQUEST_TIMEOUT_SECONDS = 10

# Alpha Vantage's free tier allows 25 requests/day, so successful quotes are reused for a while
STOCK_CACHE_SECONDS = 15 * 60
stock_cache = {}

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def parse_percent(text):
    """Convert Alpha Vantage's '-0.2397%' into -0.2397."""
    try:
        return float(text.rstrip("%"))
    except (AttributeError, ValueError):
        return None


def get_cached_stock(symbol):
    cached = stock_cache.get(symbol)
    if cached and time.monotonic() - cached["fetched_at"] < STOCK_CACHE_SECONDS:
        return cached["result"]
    return None


# Plain `def` (not `async def`): requests is blocking, so FastAPI runs these in a threadpool
@app.get("/stocks/{symbol}")
def get_stock_price(symbol: str):
    symbol = symbol.upper()
    cached = get_cached_stock(symbol)
    if cached:
        return cached

    try:
        params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": STOCK_API_KEY}
        response = requests.get(STOCK_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS).json()
        print("Stock API Response:", response)  # Log the full response

        # Extract stock price
        quote = response.get("Global Quote")
        if quote:
            result = {
                "symbol": symbol,
                "price": quote.get("05. price"),
                "change_percent": parse_percent(quote.get("10. change percent")),
            }
            stock_cache[symbol] = {"fetched_at": time.monotonic(), "result": result}
            return result
        # Alpha Vantage reports rate limiting as an "Information" message with HTTP 200
        if "Information" in response:
            return {"error": "Stock API rate limit reached"}
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
            # "delta.day" is a ratio to 24h ago, e.g. 1.0015 means +0.15%
            day_ratio = (response.get("delta") or {}).get("day")
            return {
                "symbol": symbol.upper(),
                "price": response.get("rate"),
                "change_percent": (day_ratio - 1) * 100 if day_ratio is not None else None,
            }
        return {"error": "Crypto data not found"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Failed to fetch crypto data"}


# Mounted last so the API routes above take precedence; serves the dashboard at "/"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
