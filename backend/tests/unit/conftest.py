import pandas as pd
import pytest

NEW_YORK = "America/New_York"


def ny(text):
    """A New York timestamp from 'YYYY-MM-DD HH:MM'."""
    return pd.Timestamp(text, tz=NEW_YORK)


def bars(rows):
    """Bars from (time, high, low, close) rows; open is set to close as it is unused."""
    index = pd.DatetimeIndex([ny(row[0]) for row in rows])
    return pd.DataFrame(
        {"Open": [row[3] for row in rows], "High": [row[1] for row in rows],
         "Low": [row[2] for row in rows], "Close": [row[3] for row in rows]},
        index=index,
    )


@pytest.fixture
def make_bars():
    return bars


@pytest.fixture
def at():
    return ny
