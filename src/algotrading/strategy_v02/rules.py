"""v0.2 long / short entry rules and stop / target planning per Appendix
B §B.6 and §B.7.

The strategy is implemented over already-computed indicator series. The
caller (training / paper / live runner) builds the bar streams, applies
the indicators, and then asks ``long_signal`` / ``short_signal`` whether
the most recent 5m signal bar produces an entry.

Indicator inputs use *integer* tick prices end-to-end; floating-point
math is confined to indicator computation and is converted back via the
caller. ATR and EMA inputs may be floats.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


_TICK_SIZE = 1  # MES tick = 0.25 index points; we work in ticks (integer).


class EntrySide(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class Bar5m:
    high: int
    low: int
    close: int


@dataclass(frozen=True)
class TrendFilter60m:
    ema50: float
    ema200: float
    close: float

    def long_aligned(self) -> bool:
        return self.ema50 > self.ema200 and self.close > self.ema200

    def short_aligned(self) -> bool:
        return self.ema50 < self.ema200 and self.close < self.ema200


@dataclass(frozen=True)
class EntrySignal:
    side: EntrySide
    pullback_low_or_high: int


@dataclass(frozen=True)
class StopTargetPlan:
    side: EntrySide
    expected_entry: int
    candidate_stop: int
    candidate_R: int
    actual_R: int | None
    target: int | None
    skip_reason: str | None


def round_to_tick(price: float, side: EntrySide) -> int:
    """Per Appendix B: long target rounded DOWN, short target rounded UP."""
    if side is EntrySide.LONG:
        return math.floor(price / _TICK_SIZE) * _TICK_SIZE
    return math.ceil(price / _TICK_SIZE) * _TICK_SIZE


def _pullback_long(bars: list[Bar5m], ema20: list[float | None], vwap: list[float | None]) -> int | None:
    if len(bars) < 3:
        return None
    window = bars[-3:]
    indices = [len(bars) - 3, len(bars) - 2, len(bars) - 1]
    pullback_seen = False
    for b, idx in zip(window, indices):
        thresholds: list[float] = []
        if ema20[idx] is not None:
            thresholds.append(ema20[idx])
        if vwap[idx] is not None:
            thresholds.append(vwap[idx])
        if not thresholds:
            continue
        if any(b.low <= t for t in thresholds):
            pullback_seen = True
            break
    if not pullback_seen:
        return None
    return min(b.low for b in window)


def _pullback_short(bars: list[Bar5m], ema20: list[float | None], vwap: list[float | None]) -> int | None:
    if len(bars) < 3:
        return None
    window = bars[-3:]
    indices = [len(bars) - 3, len(bars) - 2, len(bars) - 1]
    pullback_seen = False
    for b, idx in zip(window, indices):
        thresholds: list[float] = []
        if ema20[idx] is not None:
            thresholds.append(ema20[idx])
        if vwap[idx] is not None:
            thresholds.append(vwap[idx])
        if not thresholds:
            continue
        if any(b.high >= t for t in thresholds):
            pullback_seen = True
            break
    if not pullback_seen:
        return None
    return max(b.high for b in window)


def long_signal(
    *,
    bars5m: list[Bar5m],
    ema200_5m: list[float | None],
    ema20_5m: list[float | None],
    vwap_5m: list[float | None],
    trend_60m: TrendFilter60m,
) -> EntrySignal | None:
    if len(bars5m) < 4:
        return None
    if not trend_60m.long_aligned():
        return None
    last = bars5m[-1]
    prev = bars5m[-2]
    last_ema200 = ema200_5m[-1]
    if last_ema200 is None or last.close <= last_ema200:
        return None
    pullback_low = _pullback_long(bars5m, ema20_5m, vwap_5m)
    if pullback_low is None:
        return None
    if last.close <= prev.high:
        return None
    return EntrySignal(side=EntrySide.LONG, pullback_low_or_high=pullback_low)


def short_signal(
    *,
    bars5m: list[Bar5m],
    ema200_5m: list[float | None],
    ema20_5m: list[float | None],
    vwap_5m: list[float | None],
    trend_60m: TrendFilter60m,
) -> EntrySignal | None:
    if len(bars5m) < 4:
        return None
    if not trend_60m.short_aligned():
        return None
    last = bars5m[-1]
    prev = bars5m[-2]
    last_ema200 = ema200_5m[-1]
    if last_ema200 is None or last.close >= last_ema200:
        return None
    pullback_high = _pullback_short(bars5m, ema20_5m, vwap_5m)
    if pullback_high is None:
        return None
    if last.close >= prev.low:
        return None
    return EntrySignal(side=EntrySide.SHORT, pullback_low_or_high=pullback_high)


def _r_passes_atr_filter(candidate_R: int, atr14: float) -> str | None:
    if candidate_R <= 0:
        return "candidate_R_non_positive"
    if candidate_R > 1.5 * atr14:
        return "candidate_R_too_large"
    if candidate_R < 0.5 * atr14:
        return "candidate_R_too_small"
    return None


def plan_long(
    *,
    pullback_low: int,
    current_ask: int,
    modeled_slippage_ticks: int,
    atr14: float,
    actual_entry_fill: int | None = None,
) -> StopTargetPlan:
    expected_entry = current_ask + modeled_slippage_ticks
    candidate_stop = pullback_low - 1
    candidate_R = expected_entry - candidate_stop
    skip = _r_passes_atr_filter(candidate_R, atr14)
    if skip is not None or actual_entry_fill is None:
        return StopTargetPlan(
            side=EntrySide.LONG,
            expected_entry=expected_entry,
            candidate_stop=candidate_stop,
            candidate_R=candidate_R,
            actual_R=None,
            target=None,
            skip_reason=skip,
        )
    actual_R = actual_entry_fill - candidate_stop
    if actual_R <= 0:
        return StopTargetPlan(
            side=EntrySide.LONG,
            expected_entry=expected_entry,
            candidate_stop=candidate_stop,
            candidate_R=candidate_R,
            actual_R=actual_R,
            target=None,
            skip_reason="actual_R_non_positive_error_halted",
        )
    target = round_to_tick(actual_entry_fill + 1.5 * actual_R, EntrySide.LONG)
    return StopTargetPlan(
        side=EntrySide.LONG,
        expected_entry=expected_entry,
        candidate_stop=candidate_stop,
        candidate_R=candidate_R,
        actual_R=actual_R,
        target=target,
        skip_reason=None,
    )


def plan_short(
    *,
    pullback_high: int,
    current_bid: int,
    modeled_slippage_ticks: int,
    atr14: float,
    actual_entry_fill: int | None = None,
) -> StopTargetPlan:
    expected_entry = current_bid - modeled_slippage_ticks
    candidate_stop = pullback_high + 1
    candidate_R = candidate_stop - expected_entry
    skip = _r_passes_atr_filter(candidate_R, atr14)
    if skip is not None or actual_entry_fill is None:
        return StopTargetPlan(
            side=EntrySide.SHORT,
            expected_entry=expected_entry,
            candidate_stop=candidate_stop,
            candidate_R=candidate_R,
            actual_R=None,
            target=None,
            skip_reason=skip,
        )
    actual_R = candidate_stop - actual_entry_fill
    if actual_R <= 0:
        return StopTargetPlan(
            side=EntrySide.SHORT,
            expected_entry=expected_entry,
            candidate_stop=candidate_stop,
            candidate_R=candidate_R,
            actual_R=actual_R,
            target=None,
            skip_reason="actual_R_non_positive_error_halted",
        )
    target = round_to_tick(actual_entry_fill - 1.5 * actual_R, EntrySide.SHORT)
    return StopTargetPlan(
        side=EntrySide.SHORT,
        expected_entry=expected_entry,
        candidate_stop=candidate_stop,
        candidate_R=candidate_R,
        actual_R=actual_R,
        target=target,
        skip_reason=None,
    )
