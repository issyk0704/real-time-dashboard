# Real-Time Dashboard

FastAPI backend serving live stock prices (Alpha Vantage) and crypto prices (Live Coin Watch),
with a plain HTML/JS dashboard in `frontend/` served at `/`.

| Endpoint | Example | Returns |
|---|---|---|
| `GET /` | `/` | The dashboard |
| `GET /stocks/{symbol}` | `/stocks/AAPL` | `{"symbol": "AAPL", "price": "332.8900", "change_percent": -0.2397}` |
| `GET /crypto/{symbol}` | `/crypto/btc` | `{"symbol": "BTC", "price": 86271.65, "change_percent": 0.15}` |

Stock `change_percent` is versus the previous close; crypto is over the last 24 hours.
Stock quotes are cached for 15 minutes because the free Alpha Vantage tier allows 25 requests a day.
Crypto tiles refresh every 60 seconds; stock tiles refresh on demand. Watchlists are saved in the browser.

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

Dashboard: http://127.0.0.1:8000 · API docs: http://127.0.0.1:8000/docs

## Tests

```powershell
cd backend
python -m pytest
```

External APIs are mocked, so tests need no keys or network.
