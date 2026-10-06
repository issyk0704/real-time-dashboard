"""Key levels (PDH/PDL, PWH/PWL, PMH/PML) and killzone ranges from price bars.

All bar frames have a New York tz-aware index and Open/High/Low/Close columns.
A trading day runs 18:00 -> 17:00 New York time (CME convention), so the
Sunday 18:00 open belongs to Monday and the Asia killzone belongs to the next day.
"""
from datetime import timedelta

import pandas as pd

from sessions import KILLZONES

TRADING_DAY_SHIFT = timedelta(hours=6)  # 18:00 + 6h = midnight of the trading day


def trading_day(timestamp):
    return (timestamp + TRADING_DAY_SHIFT).date()


def _period_keys(index, period):
    days = pd.Series([trading_day(ts) for ts in index], index=index)
    if period == "day":
        return days
    if period == "week":
        return days.map(lambda day: tuple(day.isocalendar())[:2])
    return days.map(lambda day: (day.year, day.month))


def _period_key(timestamp, period):
    day = trading_day(timestamp)
    if period == "day":
        return day
    if period == "week":
        return tuple(day.isocalendar())[:2]
    return (day.year, day.month)


def _extremes(bars, keys, key):
    selected = bars[keys == key]
    if selected.empty:
        return None
    return {"high": float(selected["High"].max()), "low": float(selected["Low"].min()),
            "close": float(selected["Close"].iloc[-1])}


def previous_and_current(bars, now, period):
    """High/low/close of the last completed period before `now`'s period, and of the current one."""
    if bars.empty:
        return None, None
    keys = _period_keys(bars.index, period)
    current_key = _period_key(now, period)
    earlier = sorted(key for key in keys.unique() if key < current_key)
    previous = _extremes(bars, keys, earlier[-1]) if earlier else None
    return previous, _extremes(bars, keys, current_key)


LEVEL_NAMES = {"day": ("PDH", "PDL"), "week": ("PWH", "PWL"), "month": ("PMH", "PML")}


def key_levels(hourly, intraday, now):
    """Previous day/week/month highs and lows, each flagged if the current period has swept it."""
    # Intraday bars are fresher than hourly ones, so both feed the current period's extremes
    combined = pd.concat([hourly, intraday]).sort_index() if not intraday.empty else hourly
    levels = {}
    for period, (high_name, low_name) in LEVEL_NAMES.items():
        previous, _ = previous_and_current(hourly, now, period)
        _, current = previous_and_current(combined, now, period)
        if previous is None:
            continue
        levels[high_name] = {"price": previous["high"],
                             "swept": bool(current and current["high"] > previous["high"])}
        levels[low_name] = {"price": previous["low"],
                            "swept": bool(current and current["low"] < previous["low"])}
    return levels


def previous_close(hourly, now):
    previous, _ = previous_and_current(hourly, now, "day")
    return previous["close"] if previous else None


def _in_window(bars, window):
    times = [ts.time() for ts in bars.index]
    return bars[[window.contains(moment) for moment in times]]


def killzone_ranges(intraday, day):
    """High/low of each killzone within one trading day; None where there are no bars."""
    if intraday.empty:
        return {window.name: None for window in KILLZONES}
    days = pd.Series([trading_day(ts) for ts in intraday.index], index=intraday.index)
    day_bars = intraday[days == day]
    ranges = {}
    for window in KILLZONES:
        bars = _in_window(day_bars, window)
        ranges[window.name] = None if bars.empty else {
            "high": float(bars["High"].max()), "low": float(bars["Low"].min())}
    return ranges


def killzone_history(intraday, now, days_back=2):
    """Chronological (trading day, killzone, range) entries for recent days, skipping empty ones."""
    today = trading_day(now)
    history = []
    for offset in range(days_back - 1, -1, -1):
        day = today - timedelta(days=offset)
        for name, price_range in killzone_ranges(intraday, day).items():
            if price_range:
                history.append({"day": day, "name": name, **price_range})
    return history


def latest_day_closes(intraday, now):
    """Closes for the current trading day, or the most recent day with data (e.g. at weekends)."""
    if intraday.empty:
        return []
    days = pd.Series([trading_day(ts) for ts in intraday.index], index=intraday.index)
    target = trading_day(now)
    if not (days == target).any():
        target = days.iloc[-1]
    return [round(float(close), 6) for close in intraday[days == target]["Close"]]
