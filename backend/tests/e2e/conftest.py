"""Browser tests: the real server serves the frontend; every /api call is answered with fake data."""
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
# 09:00 New York (EDT): inside the NY AM killzone and the 08:50-09:10 macro
FIXED_NOW = datetime(2026, 10, 6, 13, 0, tzinfo=timezone.utc)

QUOTES = {
    "NQ=F": {"name": "NQ", "price": 31515.5, "change_percent": 0.56},
    "ES=F": {"name": "ES", "price": 7863.75, "change_percent": -0.25},
    "EURUSD=X": {"name": "EURUSD", "price": 1.12663, "change_percent": 0.38},
    "GC=F": {"name": "GC=F", "price": 2650.1, "change_percent": 0.1},
}
SESSIONS = {
    "killzones": [
        {"name": "Asia", "start": "20:00", "end": "00:00"},
        {"name": "London", "start": "02:00", "end": "05:00"},
        {"name": "NY AM", "start": "08:30", "end": "11:00"},
        {"name": "NY PM", "start": "13:30", "end": "16:00"},
    ],
    "macros": [{"name": "Macro", "start": "08:50", "end": "09:10"}, {"name": "Macro", "start": "09:50", "end": "10:10"}],
}


def fake_quote(symbol):
    if symbol not in QUOTES:
        return {"symbol": symbol, "name": symbol, "error": "No data for this symbol"}
    quote = QUOTES[symbol]
    price = quote["price"]
    # Offsets of 0.5 and 0.25 are exact in binary, so the expected text is predictable
    return {
        "symbol": symbol, **quote, "as_of": "2026-10-06T08:55:00-04:00",
        "sparkline": [price - 0.5, price + 0.5, price],
        "levels": {"PDH": {"price": price + 0.5, "swept": True},
                   "PDL": {"price": price - 0.5, "swept": False}},
        "killzones": {"Asia": {"high": price + 0.25, "low": price - 0.25},
                      "London": None, "NY AM": None, "NY PM": None},
    }


def fake_snapshot(symbols, calendar):
    return {
        "generated_at": FIXED_NOW.isoformat(),
        "quotes": [fake_quote(symbol) for symbol in symbols],
        "smt": [{"pair": "NQ / ES", "killzone": "London", "reference": "Asia", "side": "highs",
                 "swept": "ES", "failed": "NQ", "bias": "bearish", "bias_market": "NQ"}],
        "calendar": calendar,
        "sessions": SESSIONS,
    }


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
    port = free_port()
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--port", str(port)],
                              cwd=BACKEND_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 20
    while True:
        try:
            urlopen(url, timeout=1)
            break
        except OSError:
            if time.monotonic() > deadline:
                server.kill()
                raise RuntimeError("Server did not start")
            time.sleep(0.2)
    yield url
    server.terminate()
    server.wait()


class FakeApi:
    """Answers /api/stream and /api/history, and records the symbols each stream asked for."""

    def __init__(self, page):
        self.calendar = []
        self.stream_requests = []
        page.route("**/api/stream?**", self._stream)
        page.route("**/api/history/**", self._history)

    def _stream(self, route):
        symbols = parse_qs(urlparse(route.request.url).query)["symbols"][0].split(",")
        self.stream_requests.append(symbols)
        body = f"data: {json.dumps(fake_snapshot(symbols, self.calendar))}\n\n"
        route.fulfill(status=200, headers={"Content-Type": "text/event-stream"}, body=body)

    def _history(self, route):
        candles = [{"time": 1791270000 + i * 300, "open": 100 + i, "high": 101 + i, "low": 99 + i, "close": 100.5 + i}
                   for i in range(50)]
        body = {"symbol": "NQ=F", "name": "NQ", "candles": candles,
                "levels": {"PDH": {"price": 140, "swept": False}, "PDL": {"price": 95, "swept": True}}}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(body))


@pytest.fixture
def api(page):
    page.clock.set_fixed_time(FIXED_NOW)
    # Seed a small watchlist once; a reload keeps whatever the test changed it to
    page.add_init_script(
        "if (!localStorage.getItem('watchlist-v2')) {"
        " localStorage.setItem('watchlist-v2', JSON.stringify(['NQ=F', 'ES=F', 'EURUSD=X'])); }"
    )
    return FakeApi(page)
