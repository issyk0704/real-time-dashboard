from datetime import date

from smt import Pair, detect_smt

DAY = date(2026, 10, 6)


def history(asia, london):
    """Asia then London killzone ranges, as (high, low) tuples."""
    return [
        {"day": DAY, "name": "Asia", "high": asia[0], "low": asia[1]},
        {"day": DAY, "name": "London", "high": london[0], "low": london[1]},
    ]


def names(symbol):
    return {"NQ=F": "NQ", "ES=F": "ES", "DX-Y.NYB": "DXY", "EURUSD=X": "EURUSD"}[symbol]


def test_one_market_sweeps_highs_and_the_other_fails_is_bearish():
    nq = history(asia=(100, 90), london=(99, 95))     # failed to take Asia high
    es = history(asia=(50, 40), london=(51, 45))      # took Asia high

    signals = detect_smt(Pair("NQ=F", "ES=F"), nq, es, names)

    assert len(signals) == 1
    assert signals[0]["swept"] == "ES"
    assert signals[0]["failed"] == "NQ"
    assert signals[0]["bias"] == "bearish"
    assert (signals[0]["reference"], signals[0]["killzone"]) == ("Asia", "London")


def test_one_market_sweeps_lows_and_the_other_fails_is_bullish():
    nq = history(asia=(100, 90), london=(98, 89))     # took Asia low
    es = history(asia=(50, 40), london=(49, 41))      # held above Asia low

    signals = detect_smt(Pair("NQ=F", "ES=F"), nq, es, names)

    assert [(signal["bias"], signal["swept"], signal["failed"]) for signal in signals] == [("bullish", "NQ", "ES")]


def test_both_markets_sweeping_is_not_a_divergence():
    nq = history(asia=(100, 90), london=(101, 95))
    es = history(asia=(50, 40), london=(51, 45))
    assert detect_smt(Pair("NQ=F", "ES=F"), nq, es, names) == []


def test_inverse_pair_compares_highs_with_lows():
    dxy = history(asia=(100, 90), london=(101, 95))   # took Asia high
    eur = history(asia=(1.2, 1.1), london=(1.15, 1.12))  # did not take Asia low

    signals = detect_smt(Pair("DX-Y.NYB", "EURUSD=X", inverse=True), dxy, eur, names)

    assert len(signals) == 1
    assert signals[0]["swept"] == "DXY"
    assert signals[0]["failed"] == "EURUSD"
    assert signals[0]["bias"] == "bearish"
    assert signals[0]["bias_market"] == "DXY"


def test_inverse_pair_moving_together_is_not_a_divergence():
    dxy = history(asia=(100, 90), london=(101, 95))   # took Asia high
    eur = history(asia=(1.2, 1.1), london=(1.15, 1.09))  # took Asia low
    assert detect_smt(Pair("DX-Y.NYB", "EURUSD=X", inverse=True), dxy, eur, names) == []


def test_needs_two_killzones_both_markets_traded():
    nq = history(asia=(100, 90), london=(101, 95))
    es = history(asia=(50, 40), london=(49, 45))[:1]  # only Asia
    assert detect_smt(Pair("NQ=F", "ES=F"), nq, es, names) == []
