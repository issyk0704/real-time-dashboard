from datetime import date

import pandas as pd

from levels import (key_levels, killzone_history, killzone_ranges, latest_day_closes, previous_close,
                    trading_day)

EMPTY = pd.DataFrame(columns=["Open", "High", "Low", "Close"])


def test_trading_day_rolls_over_at_18_00_new_york(at):
    assert trading_day(at("2026-10-05 17:59")) == date(2026, 10, 5)
    assert trading_day(at("2026-10-05 18:00")) == date(2026, 10, 6)


def test_previous_day_levels_and_sweep_flags(make_bars, at):
    hourly = make_bars([
        ("2026-10-04 19:00", 105, 100, 102),  # Sunday evening: Monday's trading day
        ("2026-10-05 10:00", 110, 99, 108),
        ("2026-10-05 19:00", 109, 104, 106),  # Tuesday's trading day
    ])
    intraday = make_bars([("2026-10-06 08:55", 111, 105, 110)])

    levels = key_levels(hourly, intraday, at("2026-10-06 09:00"))

    assert levels["PDH"] == {"price": 110, "swept": True}  # 111 traded above it
    assert levels["PDL"] == {"price": 99, "swept": False}


def test_sunday_evening_belongs_to_the_new_week(make_bars, at):
    hourly = make_bars([
        ("2026-10-02 10:00", 120, 90, 95),     # Friday
        ("2026-10-04 19:00", 101, 100, 100),   # Sunday open
    ])

    levels = key_levels(hourly, EMPTY, at("2026-10-05 09:00"))

    assert levels["PWH"]["price"] == 120
    assert levels["PWL"]["price"] == 90
    # Friday is the previous trading day; Sunday's bars are part of Monday
    assert levels["PDH"]["price"] == 120


def test_previous_month_levels(make_bars, at):
    hourly = make_bars([
        ("2026-09-30 10:00", 130, 80, 85),
        ("2026-10-05 10:00", 131, 90, 100),
    ])

    levels = key_levels(hourly, EMPTY, at("2026-10-06 09:00"))

    assert levels["PMH"] == {"price": 130, "swept": True}
    assert levels["PML"] == {"price": 80, "swept": False}


def test_no_history_gives_no_levels(at):
    assert key_levels(EMPTY, EMPTY, at("2026-10-06 09:00")) == {}


def test_previous_close_is_last_close_of_previous_trading_day(make_bars, at):
    hourly = make_bars([
        ("2026-10-05 15:00", 110, 100, 105),
        ("2026-10-05 16:00", 110, 100, 107),
        ("2026-10-05 19:00", 110, 100, 109),
    ])
    assert previous_close(hourly, at("2026-10-06 09:00")) == 107


def test_killzone_ranges_use_the_trading_day(make_bars):
    intraday = make_bars([
        ("2026-10-05 03:00", 99, 1, 50),       # previous day's London: excluded
        ("2026-10-05 20:30", 50, 40, 45),      # Asia, counts towards 6 October
        ("2026-10-06 03:00", 60, 45, 55),      # London
        ("2026-10-06 04:59", 62, 50, 55),      # London, last bar
        ("2026-10-06 05:00", 70, 30, 55),      # after London: excluded
    ])

    ranges = killzone_ranges(intraday, date(2026, 10, 6))

    assert ranges["Asia"] == {"high": 50, "low": 40}
    assert ranges["London"] == {"high": 62, "low": 45}
    assert ranges["NY AM"] is None


def test_killzone_history_is_chronological_and_skips_empty(make_bars, at):
    intraday = make_bars([
        ("2026-10-05 14:00", 10, 9, 9),        # NY PM, 5 October
        ("2026-10-05 21:00", 11, 8, 9),        # Asia, 6 October
        ("2026-10-06 03:00", 12, 7, 9),        # London, 6 October
    ])

    history = killzone_history(intraday, at("2026-10-06 06:00"))

    assert [(entry["day"].day, entry["name"]) for entry in history] == [(5, "NY PM"), (6, "Asia"), (6, "London")]


def test_sparkline_falls_back_to_latest_day_with_data(make_bars, at):
    intraday = make_bars([
        ("2026-10-02 10:00", 2, 1, 1.5),
        ("2026-10-02 10:05", 2, 1, 1.75),
    ])
    # Saturday: no bars for the current trading day, so Friday's closes are shown
    assert latest_day_closes(intraday, at("2026-10-03 12:00")) == [1.5, 1.75]
