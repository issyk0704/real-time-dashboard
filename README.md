# Real-Time Dashboard

An ICT-oriented market dashboard: a FastAPI backend with a plain HTML/JS frontend, using free Yahoo Finance data
(via `yfinance`) and the free ForexFactory calendar feed. No API keys are needed.

## Features

- **Watchlist tiles**: price, change versus the previous 17:00 NY close, and an intraday sparkline. Defaults are
  NQ, ES, YM, DXY, EURUSD, GBPUSD, ZN and BTC; any Yahoo symbol can be added (e.g. `GC=F`, `AAPL`, `ETH-USD`).
- **Key levels**: PDH/PDL, PWH/PWL, PMH/PML, flagged when the current period has swept them.
- **Killzone clock**: current or next killzone (Asia, London, NY AM, NY PM) and ICT macro window, in NY time.
- **Killzone ranges**: high and low of each killzone in the current trading day.
- **SMT divergence**: NQ/ES, ES/YM, NQ/YM, EURUSD/GBPUSD and DXY/EURUSD (inverse), latest killzone versus the one before.
- **Economic calendar**: USD/EUR/GBP high and medium impact events, with a banner 15 minutes either side of high-impact news.
- **Charts**: click a tile for 5-minute candles with the key levels drawn on (TradingView Lightweight Charts).
- **Live updates**: the server pushes a fresh snapshot every 15 seconds over Server-Sent Events.

Definitions live in one place each: killzones and macros in `backend/sessions.py`, SMT pairs in `backend/smt.py`.
A trading day runs 18:00 to 17:00 New York time (CME convention).

**Data caveat:** Yahoo's CME futures data is delayed by about 10 minutes; FX and crypto are close to live.
`yfinance` is an unofficial client, so it can occasionally break when Yahoo changes something.

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | The dashboard |
| `GET /api/snapshot?symbols=NQ=F,ES=F` | One snapshot: quotes, levels, killzones, SMT, calendar, session windows |
| `GET /api/stream?symbols=NQ=F,ES=F` | The same snapshot as Server-Sent Events, every 15 seconds |
| `GET /api/history/{symbol}` | 5-minute candles and key levels for the chart |

## Run locally (Windows / PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn main:app --reload
```

Dashboard: http://127.0.0.1:8000 · API docs: http://127.0.0.1:8000/docs

## Tests

```powershell
cd backend
python -m pytest                                        # unit tests (no network)
python -m pytest tests/e2e --browser-channel msedge     # browser tests using the installed Edge
```

The browser tests start the real server but answer every `/api` call with fake data and pin the browser clock,
so they are deterministic. On a machine without Edge, run `python -m playwright install chromium` once and drop
`--browser-channel msedge`.

GitHub Actions (`.github/workflows/ci.yml`) runs both suites on every push to `main` and on pull requests.

## Docker / Railway

```powershell
docker build -t real-time-dashboard .
docker run --rm -p 8000:8000 real-time-dashboard
```

The container listens on `$PORT` (default 8000), which is what Railway provides. To deploy on Railway, create a
project from this GitHub repo; it detects the `Dockerfile` automatically. No environment variables are required.
