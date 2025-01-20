from fastapi import FastAPI
import requests

app = FastAPI()

# API keys and base URLs
STOCK_API_KEY = "DJC1P4E8708Y87QJ"  # 
STOCK_API_URL = "https://www.alphavantage.co/query"
LIVECOINWATCH_API_URL = "https://api.livecoinwatch.com/coins/single"
LIVECOINWATCH_API_KEY = "be29f003-38b3-4174-8f5e-1f7e7ca8c362"  # 

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Real-Time Dashboard API"}

@app.get("/stocks/{symbol}")
async def get_stock_price(symbol: str):
    try:
        # Construct the Alpha Vantage API URL
        url = f"{STOCK_API_URL}?function=GLOBAL_QUOTE&symbol={symbol}&apikey={STOCK_API_KEY}"
        response = requests.get(url).json()
        print("Stock API Response:", response)  # Log the full response

        # Extract stock price
        if "Global Quote" in response:
            return {
                "symbol": symbol,
                "price": response["Global Quote"].get("05. price")
            }
        return {"error": "Stock data not found"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Failed to fetch stock data"}

@app.get("/crypto/{symbol}")
async def get_crypto_price(symbol: str):
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
        response = requests.post(LIVECOINWATCH_API_URL, json=payload, headers=headers).json()
        print("Crypto API Response:", response)  # Log the full response

        # Extract cryptocurrency price
        if response and "rate" in response:
            return {
                "symbol": response.get("code"),
                "price": response.get("rate")
            }
        return {"error": "Crypto data not found"}
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Failed to fetch crypto data"}

