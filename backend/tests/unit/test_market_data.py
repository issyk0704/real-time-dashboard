from unittest.mock import patch

import pandas as pd
import pytest

import market_data
from market_data import INTRADAY, get_bars, normalise


@pytest.fixture(autouse=True)
def clear_cache():
    market_data._cache.clear()


def frame(index):
    return pd.DataFrame({"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [10]}, index=index)


def test_normalise_converts_utc_to_new_york_and_keeps_ohlc():
    bars = normalise(frame(pd.DatetimeIndex([pd.Timestamp("2026-10-06 13:00", tz="UTC")])))
    assert list(bars.columns) == ["Open", "High", "Low", "Close"]
    assert str(bars.index[0]) == "2026-10-06 09:00:00-04:00"


def test_normalise_treats_naive_times_as_utc():
    bars = normalise(frame(pd.DatetimeIndex([pd.Timestamp("2026-10-06 13:00")])))
    assert str(bars.index[0]) == "2026-10-06 09:00:00-04:00"


@patch("market_data._download")
def test_only_stale_symbols_are_downloaded(mock_download):
    mock_download.side_effect = lambda symbols, spec: {symbol: f"bars-{symbol}" for symbol in symbols}

    get_bars(["NQ=F"], INTRADAY)
    result = get_bars(["NQ=F", "ES=F"], INTRADAY)

    assert [call.args[0] for call in mock_download.call_args_list] == [["NQ=F"], ["ES=F"]]
    assert result == {"NQ=F": "bars-NQ=F", "ES=F": "bars-ES=F"}


@patch("market_data._download")
def test_download_failure_returns_empty_bars(mock_download):
    mock_download.side_effect = RuntimeError("Yahoo unavailable")
    result = get_bars(["NQ=F"], INTRADAY)
    assert result["NQ=F"].empty
