"""Builds the dashboard snapshot: quotes, levels, killzone ranges, SMT and calendar."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

import econ_calendar
import market_data
from levels import key_levels, killzone_history, killzone_ranges, latest_day_closes, previous_close, trading_day
from sessions import sessions_config
from smt import SMT_PAIRS, detect_smt

NEW_YORK = ZoneInfo("America/New_York")
EPOCH = pd.Timestamp("1970-01-01")

DISPLAY_NAMES = {
    "NQ=F": "NQ",
    "ES=F": "ES",
    "YM=F": "YM",
    "DX-Y.NYB": "DXY",
    "EURUSD=X": "EURUSD",
    "GBPUSD=X": "GBPUSD",
    "ZN=F": "ZN",
    "BTC-USD": "BTC",
    "ETH-USD": "ETH",
}


def current_time():
    return datetime.now(NEW_YORK)


def display_name(symbol):
    return DISPLAY_NAMES.get(symbol, symbol)


def build_quote(symbol, intraday, hourly, now):
    closes = intraday["Close"].dropna()
    if closes.empty:
        return {"symbol": symbol, "name": display_name(symbol), "error": "No data for this symbol"}
    price = float(closes.iloc[-1])
    prior_close = previous_close(hourly, now)
    return {
        "symbol": symbol,
        "name": display_name(symbol),
        "price": price,
        "change_percent": (price / prior_close - 1) * 100 if prior_close else None,
        "as_of": closes.index[-1].isoformat(),
        "sparkline": latest_day_closes(intraday, now),
        "levels": key_levels(hourly, intraday, now),
        "killzones": killzone_ranges(intraday, trading_day(now)),
    }


def build_smt(intraday_by_symbol, now):
    signals = []
    for pair in SMT_PAIRS:
        first, second = intraday_by_symbol[pair.first], intraday_by_symbol[pair.second]
        signals += detect_smt(pair, killzone_history(first, now), killzone_history(second, now), display_name)
    return signals


def build_snapshot(symbols, now=None):
    now = now or current_time()
    smt_symbols = {symbol for pair in SMT_PAIRS for symbol in (pair.first, pair.second)}
    all_symbols = list(dict.fromkeys([*symbols, *sorted(smt_symbols)]))
    intraday = market_data.get_bars(all_symbols, market_data.INTRADAY)
    hourly = market_data.get_bars(symbols, market_data.HOURLY)

    return {
        "generated_at": now.isoformat(),
        "quotes": [build_quote(symbol, intraday[symbol], hourly[symbol], now) for symbol in symbols],
        "smt": build_smt(intraday, now),
        "calendar": econ_calendar.upcoming_events(now),
        "sessions": sessions_config(),
    }


def build_history(symbol, now=None):
    """5-minute candles plus key levels for the chart view."""
    now = now or current_time()
    intraday = market_data.get_bars([symbol], market_data.INTRADAY)[symbol]
    hourly = market_data.get_bars([symbol], market_data.HOURLY)[symbol]
    candles = [
        {
            "time": chart_time(ts),
            "open": float(row.Open), "high": float(row.High), "low": float(row.Low), "close": float(row.Close),
        }
        for ts, row in intraday.dropna().iterrows()
    ]
    return {"symbol": symbol, "name": display_name(symbol), "candles": candles,
            "levels": key_levels(hourly, intraday, now)}


def chart_time(timestamp):
    """Lightweight Charts labels times as UTC, so send New York wall-clock time as if it were UTC."""
    return int((timestamp.tz_localize(None) - EPOCH).total_seconds())
