# Real-Time Dashboard API

FastAPI backend serving live stock prices (Alpha Vantage) and crypto prices (Live Coin Watch).

| Endpoint | Example | Returns |
|---|---|---|
| `GET /` | `/` | Welcome message |
| `GET /stocks/{symbol}` | `/stocks/AAPL` | `{"symbol": "AAPL", "price": "332.8900"}` |
| `GET /crypto/{symbol}` | `/crypto/btc` | `{"symbol": "BTC", "price": 86271.65}` |

## Setup (Windows / PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Both APIs have free keys: [Alpha Vantage](https://www.alphavantage.co/support/#api-key) (25 requests/day) and [Live Coin Watch](https://www.livecoinwatch.com/tools/api).

```powershell
$env:ALPHAVANTAGE_API_KEY = "<your key>"
$env:LIVECOINWATCH_API_KEY = "<your key>"
uvicorn main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

## Tests

```powershell
cd backend
python -m pytest
```

External APIs are mocked, so tests need no keys or network.
