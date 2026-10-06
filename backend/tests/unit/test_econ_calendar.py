from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

import econ_calendar
from econ_calendar import filter_events

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=ZoneInfo("America/New_York"))


def event(title, date, country="USD", impact="High"):
    return {"title": title, "country": country, "date": date, "impact": impact, "forecast": "", "previous": ""}


@pytest.fixture(autouse=True)
def reset_cache():
    econ_calendar._cache.update({"next_fetch_at": 0.0, "events": []})


def test_keeps_only_relevant_currencies_and_impacts():
    events = [
        event("CPI", "2026-10-06T08:30:00-04:00"),
        event("Retail Sales", "2026-10-06T10:00:00-04:00", impact="Medium"),
        event("Bank Holiday", "2026-10-06T10:00:00-04:00", impact="Holiday"),
        event("BOJ Speech", "2026-10-06T10:00:00-04:00", country="JPY"),
        event("Low thing", "2026-10-06T10:00:00-04:00", impact="Low"),
    ]
    assert [item["title"] for item in filter_events(events, NOW)] == ["CPI", "Retail Sales"]


def test_drops_events_more_than_an_hour_old_and_sorts_soonest_first():
    events = [
        event("Later", "2026-10-07T14:00:00-04:00"),
        event("Two hours ago", "2026-10-06T07:00:00-04:00"),
        event("Soon", "2026-10-06T13:30:00+01:00"),  # 08:30 NY: within the last hour
    ]
    assert [item["title"] for item in filter_events(events, NOW)] == ["Soon", "Later"]


@patch("econ_calendar.requests.get")
def test_feed_is_cached(mock_get):
    mock_get.return_value = MagicMock(json=MagicMock(return_value=[event("CPI", "2026-10-06T10:00:00-04:00")]))
    econ_calendar.upcoming_events(NOW)
    econ_calendar.upcoming_events(NOW)
    assert mock_get.call_count == 1


@patch("econ_calendar.requests.get")
def test_failed_fetch_keeps_last_good_events_and_backs_off(mock_get):
    econ_calendar._cache["events"] = [event("CPI", "2026-10-06T10:00:00-04:00")]
    mock_get.side_effect = ConnectionError()

    first = econ_calendar.upcoming_events(NOW)
    econ_calendar.upcoming_events(NOW)

    assert [item["title"] for item in first] == ["CPI"]
    assert mock_get.call_count == 1  # no retry until the back-off expires
