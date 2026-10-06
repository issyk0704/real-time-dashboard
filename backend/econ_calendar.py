"""This week's economic calendar from the free ForexFactory feed."""
import threading
import time
from datetime import datetime, timedelta

import requests

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_SECONDS = 60 * 60  # the feed asks clients not to poll often
RETRY_SECONDS = 5 * 60
CURRENCIES = {"USD", "EUR", "GBP"}
IMPACTS = {"High", "Medium"}
SHOW_PAST = timedelta(hours=1)
MAX_EVENTS = 20

_cache = {"next_fetch_at": 0.0, "events": []}
_lock = threading.Lock()


def filter_events(events, now):
    """Relevant events from an hour ago onwards, soonest first."""
    selected = []
    for event in events:
        if event.get("country") not in CURRENCIES or event.get("impact") not in IMPACTS:
            continue
        when = datetime.fromisoformat(event["date"])
        if when < now - SHOW_PAST:
            continue
        selected.append({
            "time": when.isoformat(),
            "currency": event["country"],
            "impact": event["impact"],
            "title": event.get("title", ""),
            "forecast": event.get("forecast", ""),
            "previous": event.get("previous", ""),
        })
    selected.sort(key=lambda event: event["time"])
    return selected[:MAX_EVENTS]


def _fetch_raw():
    with _lock:
        if time.monotonic() >= _cache["next_fetch_at"]:
            try:
                _cache["events"] = requests.get(FEED_URL, timeout=10).json()
                _cache["next_fetch_at"] = time.monotonic() + CACHE_SECONDS
            except Exception as e:
                # Keep serving the last good copy, and back off rather than retry every snapshot
                print(f"Calendar fetch failed: {e}")
                _cache["next_fetch_at"] = time.monotonic() + RETRY_SECONDS
        return _cache["events"]


def upcoming_events(now):
    return filter_events(_fetch_raw(), now)
