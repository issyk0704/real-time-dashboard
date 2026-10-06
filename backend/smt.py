"""SMT divergence: correlated markets where one sweeps the previous killzone's extreme and the other fails to.

For a positively correlated pair (NQ/ES), compare highs with highs and lows with lows.
For an inversely correlated pair (DXY/EURUSD), compare one market's highs with the other's lows.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Pair:
    first: str
    second: str
    inverse: bool = False


SMT_PAIRS = [
    Pair("NQ=F", "ES=F"),
    Pair("ES=F", "YM=F"),
    Pair("NQ=F", "YM=F"),
    Pair("EURUSD=X", "GBPUSD=X"),
    Pair("DX-Y.NYB", "EURUSD=X", inverse=True),
]


def _latest_two_common(history_a, history_b):
    """The latest killzone both markets have data for, and the one before it."""
    keys_b = {(entry["day"], entry["name"]) for entry in history_b}
    common = [(entry["day"], entry["name"]) for entry in history_a if (entry["day"], entry["name"]) in keys_b]
    if len(common) < 2:
        return None
    return common[-2], common[-1]


def _by_key(history):
    return {(entry["day"], entry["name"]): entry for entry in history}


def _took(ranges, key_ref, key_cur, side):
    if side == "high":
        return ranges[key_cur]["high"] > ranges[key_ref]["high"]
    return ranges[key_cur]["low"] < ranges[key_ref]["low"]


def detect_smt(pair, history_first, history_second, names):
    """Return divergence signals for the latest killzone versus the one before it."""
    keys = _latest_two_common(history_first, history_second)
    if keys is None:
        return []
    key_ref, key_cur = keys
    first, second = _by_key(history_first), _by_key(history_second)
    first_name, second_name = names(pair.first), names(pair.second)

    signals = []
    for first_side in ("high", "low"):
        second_side = ({"high": "low", "low": "high"} if pair.inverse else {"high": "high", "low": "low"})[first_side]
        first_took = _took(first, key_ref, key_cur, first_side)
        second_took = _took(second, key_ref, key_cur, second_side)
        if first_took == second_took:
            continue
        swept, failed = (first_name, second_name) if first_took else (second_name, first_name)
        # Bias is stated for the first market: failing to hold a sweep of highs is bearish
        signals.append({
            "pair": f"{first_name} / {second_name}",
            "killzone": key_cur[1],
            "reference": key_ref[1],
            "side": f"{first_side}s" if not pair.inverse else f"{first_name} {first_side}s vs {second_name} {second_side}s",
            "swept": swept,
            "failed": failed,
            "bias": "bearish" if first_side == "high" else "bullish",
            "bias_market": first_name,
        })
    return signals
