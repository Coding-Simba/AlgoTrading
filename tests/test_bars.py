"""§B.5 boundary tests for the 5m / 60m bar builder."""

import pytest

from algotrading.bars import FIVE_MIN, SIXTY_MIN, BarBuilder, BarBuilderError, build_bars
from algotrading.ingestion.types import Tick


def _t(ts_ns: int, price: int, size: int = 1) -> Tick:
    return Tick(ts_ns=ts_ns, symbol="MES", price=price, size=size, aggressor="U")


def test_tick_at_open_belongs_to_this_bar() -> None:
    bars = list(
        build_bars(
            [_t(0, 100), _t(FIVE_MIN - 1, 110), _t(FIVE_MIN, 120)],
            interval_ns=FIVE_MIN,
        )
    )
    assert len(bars) == 2
    assert bars[0].open_ns == 0
    assert bars[0].close_ns == FIVE_MIN
    assert (bars[0].open, bars[0].high, bars[0].low, bars[0].close) == (100, 110, 100, 110)
    assert bars[1].open_ns == FIVE_MIN
    assert bars[1].open == 120


def test_tick_at_exact_close_goes_to_next_bar() -> None:
    bars = list(
        build_bars([_t(0, 100), _t(FIVE_MIN, 200)], interval_ns=FIVE_MIN)
    )
    assert bars[0].open_ns == 0
    assert bars[0].close == 100
    assert bars[1].open_ns == FIVE_MIN
    assert bars[1].open == 200


def test_empty_bar_emits_no_record() -> None:
    bars = list(
        build_bars([_t(0, 100), _t(2 * FIVE_MIN, 200)], interval_ns=FIVE_MIN)
    )
    assert [b.open_ns for b in bars] == [0, 2 * FIVE_MIN]


def test_anchor_alignment() -> None:
    anchor = 30 * 60 * 1_000_000_000
    builder = BarBuilder(FIVE_MIN, anchor_ns=anchor)
    builder.push(_t(anchor + 1, 100))
    builder.push(_t(anchor + FIVE_MIN - 1, 105))
    bar = builder.flush()
    assert bar is not None
    assert bar.open_ns == anchor


def test_non_monotonic_tick_rejected() -> None:
    builder = BarBuilder(FIVE_MIN)
    builder.push(_t(2 * FIVE_MIN, 100))
    with pytest.raises(BarBuilderError):
        builder.push(_t(0, 50))


def test_60m_bar_open_and_close() -> None:
    bars = list(
        build_bars(
            [_t(0, 100), _t(SIXTY_MIN - 1, 200), _t(SIXTY_MIN, 300)],
            interval_ns=SIXTY_MIN,
        )
    )
    assert bars[0].open_ns == 0
    assert bars[0].close_ns == SIXTY_MIN
    assert bars[1].open_ns == SIXTY_MIN


def test_volume_and_count_aggregation() -> None:
    bars = list(
        build_bars(
            [_t(0, 100, size=2), _t(1, 110, size=3), _t(2, 90, size=1)],
            interval_ns=FIVE_MIN,
        )
    )
    builder = BarBuilder(FIVE_MIN)
    for t in [_t(0, 100, size=2), _t(1, 110, size=3), _t(2, 90, size=1)]:
        builder.push(t)
    bar = builder.flush()
    assert bar is not None
    assert bar.volume == 6
    assert bar.tick_count == 3
    assert bar.high == 110 and bar.low == 90
    assert bar.open == 100 and bar.close == 90
