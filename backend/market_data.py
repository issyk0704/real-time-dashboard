"""Price bars from Yahoo Finance (via yfinance), batched per download and cached per symbol."""
import threading
import time
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

NEW_YORK = "America/New_York"
COLUMNS = ["Open", "High", "Low", "Close"]


@dataclass(frozen=True)
class BarSpec:
    interval: str
    period: str
    cache_seconds: int


INTRADAY = BarSpec("5m", "5d", 30)   # sparklines, killzones, charts, latest price
HOURLY = BarSpec("1h", "3mo", 600)   # previous day/week/month levels

_cache = {}  # (interval, symbol) -> {"fetched_at": float, "bars": DataFrame}
_lock = threading.Lock()


def normalise(bars):
    """Keep OHLC columns, drop empty rows, and express times in New York time."""
    bars = bars[COLUMNS].dropna(how="all")
    index = bars.index if bars.index.tz is not None else bars.index.tz_localize("UTC")
    return bars.set_axis(index.tz_convert(NEW_YORK))


def _download(symbols, spec):
    data = yf.download(symbols, period=spec.period, interval=spec.interval, group_by="ticker",
                       auto_adjust=False, progress=False, threads=True)
    result = {}
    for symbol in symbols:
        if data.empty or symbol not in data.columns.get_level_values(0):
            result[symbol] = pd.DataFrame(columns=COLUMNS)
        else:
            result[symbol] = normalise(data[symbol])
    return result


def get_bars(symbols, spec):
    """Bars for each symbol; only stale symbols are downloaded, in a single batch."""
    with _lock:
        now = time.monotonic()
        stale = [symbol for symbol in symbols
                 if now - _cache.get((spec.interval, symbol), {}).get("fetched_at", float("-inf")) >= spec.cache_seconds]
        if stale:
            try:
                for symbol, bars in _download(stale, spec).items():
                    _cache[(spec.interval, symbol)] = {"fetched_at": now, "bars": bars}
            except Exception as e:
                # Serve whatever is cached; the next call retries the download
                print(f"Download failed for {stale}: {e}")
        empty = pd.DataFrame(columns=COLUMNS)
        return {symbol: _cache.get((spec.interval, symbol), {}).get("bars", empty) for symbol in symbols}
