import asyncio
import json
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, parse_symbols, snapshot_events
from snapshot import chart_time

client = TestClient(app)


@pytest.fixture
def fake_market(make_bars, at):
    """Patch the data sources: every known symbol gets the same bars; NOTREAL gets none."""
    hourly = make_bars([("2026-10-05 10:00", 110, 99, 108)])
    intraday = make_bars([("2026-10-06 08:55", 111, 105, 109), ("2026-10-06 09:00", 112, 106, 110)])

    def get_bars(symbols, spec):
        source = intraday if spec.interval == "5m" else hourly
        return {symbol: (pd.DataFrame(columns=source.columns) if symbol == "NOTREAL" else source)
                for symbol in symbols}

    # Pin the clock so the test data stays "today" whenever the suite runs
    with patch("snapshot.market_data.get_bars", side_effect=get_bars), \
            patch("snapshot.econ_calendar.upcoming_events", return_value=[]), \
            patch("snapshot.current_time", return_value=at("2026-10-06 09:05")):
        yield


def test_root_serves_dashboard():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Market dashboard" in response.text


def test_frontend_script_is_served():
    assert client.get("/app.js").status_code == 200


def test_parse_symbols_uppercases_and_deduplicates():
    assert parse_symbols(" nq=f, ES=F,nq=f ") == ["NQ=F", "ES=F"]


@pytest.mark.parametrize("raw", ["", " , ", "NQ=F;DROP", ",".join(f"S{i}" for i in range(21))])
def test_invalid_symbol_lists_are_rejected(raw):
    response = client.get("/api/snapshot", params={"symbols": raw})
    assert response.status_code == 400


def test_snapshot_contains_quotes_levels_and_sessions(fake_market):
    response = client.get("/api/snapshot", params={"symbols": "NQ=F,NOTREAL"})
    body = response.json()

    nq, missing = body["quotes"]
    assert nq["name"] == "NQ"
    assert nq["price"] == 110
    assert nq["change_percent"] == pytest.approx((110 / 108 - 1) * 100)
    assert nq["levels"]["PDH"]["price"] == 110
    assert nq["sparkline"] == [109, 110]
    assert missing == {"symbol": "NOTREAL", "name": "NOTREAL", "error": "No data for this symbol"}
    assert body["sessions"]["killzones"][0]["name"] == "Asia"
    assert body["calendar"] == []


def test_stream_sends_snapshot_as_server_sent_event(fake_market):
    async def still_connected():
        return False

    async def first_event():
        events = snapshot_events(["NQ=F"], still_connected)
        try:
            return await anext(events)
        finally:
            await events.aclose()

    event = asyncio.run(first_event())

    assert event.startswith("data: ") and event.endswith("\n\n")
    assert json.loads(event.removeprefix("data: "))["quotes"][0]["name"] == "NQ"


def test_stream_stops_when_client_disconnects():
    async def disconnected():
        return True

    async def collect():
        return [event async for event in snapshot_events(["NQ=F"], disconnected)]

    assert asyncio.run(collect()) == []


def test_history_returns_candles_in_new_york_wall_clock_time(fake_market):
    body = client.get("/api/history/NQ=F").json()
    assert len(body["candles"]) == 2
    # 09:00 New York, labelled as 09:00 UTC so the chart axis reads New York time
    assert body["candles"][-1]["time"] == int(pd.Timestamp("2026-10-06 09:00", tz="UTC").timestamp())
    assert body["candles"][-1]["close"] == 110


def test_chart_time_ignores_daylight_saving_offset():
    winter = pd.Timestamp("2026-01-06 09:00", tz="America/New_York")
    assert chart_time(winter) == int(pd.Timestamp("2026-01-06 09:00", tz="UTC").timestamp())
