from pathlib import Path

from algotrading.baselines import (
    DriftMatchedRandom,
    RandomBaseline,
    ReversedSignalBaseline,
    SessionExposureBaseline,
)
from algotrading.bars import FIVE_MIN, Bar
from algotrading.calendar import load_calendar


def _bars(n: int, start_ns: int = 0):
    return [
        Bar(
            open_ns=start_ns + i * FIVE_MIN,
            close_ns=start_ns + (i + 1) * FIVE_MIN,
            open=4500, high=4505, low=4495, close=4500,
            volume=10, tick_count=10, interval_ns=FIVE_MIN,
        )
        for i in range(n)
    ]


def test_random_deterministic() -> None:
    out_a = list(RandomBaseline(seed=42)(_bars(100)))
    out_b = list(RandomBaseline(seed=42)(_bars(100)))
    assert out_a == out_b
    assert set(out_a).issubset({-1, 0, 1})


def test_drift_matched_random_uses_bias() -> None:
    long_biased = list(DriftMatchedRandom(drift_per_bar=0.01, seed=7)(_bars(500)))
    longs = sum(1 for s in long_biased if s == 1)
    shorts = sum(1 for s in long_biased if s == -1)
    assert longs > shorts


def test_reversed_signal() -> None:
    inner = RandomBaseline(seed=1)
    inner_signals = list(inner(_bars(50)))
    inverted = list(ReversedSignalBaseline(inner=RandomBaseline(seed=1))(_bars(50)))
    assert inverted == [-s for s in inner_signals]


def test_session_exposure() -> None:
    cal = load_calendar(Path(__file__).parent.parent / "configs" / "sessions" / "mes.yml")
    import datetime as dt
    open_ns = int(dt.datetime.fromisoformat("2026-05-11T10:00:00-04:00").timestamp() * 1_000_000_000)
    bars_in = _bars(3, start_ns=open_ns)
    out = list(SessionExposureBaseline(calendar=cal)(bars_in))
    assert all(s == 1 for s in out)

    closed_ns = int(dt.datetime.fromisoformat("2026-05-11T03:00:00-04:00").timestamp() * 1_000_000_000)
    bars_out = _bars(3, start_ns=closed_ns)
    out = list(SessionExposureBaseline(calendar=cal)(bars_out))
    assert all(s == 0 for s in out)
