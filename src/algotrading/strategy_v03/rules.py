"""v0.3 entry rules and stop/target planning per Appendix B v0.3.

Skeleton: pure-function signal evaluation. Entry / planning functions are
gate-blocked; pure classification helpers are not.
"""

from __future__ import annotations

import math
from pathlib import Path

from ..governance.phase_gates import GateContext, assert_v03_code_unblocked
from ..strategy_v02.rules import (
    Bar5m,
    EntrySide,
    EntrySignal,
    StopTargetPlan,
)


_TICK_SIZE = 1
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _check_gate() -> None:
    assert_v03_code_unblocked(GateContext.default(_REPO_ROOT))


def classify_extension_long(
    *,
    close: float,
    session_vwap: float,
    atr14: float,
    extension_multiplier: float = 1.5,
) -> bool:
    """True if the signal-bar close is at least ``extension_multiplier *
    ATR(14)`` below session VWAP. Pure classifier; not gate-blocked."""
    return close <= session_vwap - extension_multiplier * atr14


def classify_extension_short(
    *,
    close: float,
    session_vwap: float,
    atr14: float,
    extension_multiplier: float = 1.5,
) -> bool:
    return close >= session_vwap + extension_multiplier * atr14


def long_signal_v03(
    *,
    bars5m: list[Bar5m],
    ema50_60m: float | None,
    ema200_60m: float | None,
    close_60m: float | None,
    session_vwap_5m: list[float | None],
    atr14_5m: list[float | None],
) -> EntrySignal | None:
    _check_gate()
    if len(bars5m) < 3:
        return None
    if ema50_60m is None or ema200_60m is None or close_60m is None:
        return None
    if ema50_60m < ema200_60m and close_60m < ema200_60m:
        return None
    last = bars5m[-1]
    prev = bars5m[-2]
    vwap_last = session_vwap_5m[-1] if session_vwap_5m else None
    atr_last = atr14_5m[-1] if atr14_5m else None
    if vwap_last is None or atr_last is None:
        return None
    if not classify_extension_long(close=last.close, session_vwap=vwap_last, atr14=atr_last):
        return None
    if last.low <= prev.low:
        return None
    bar_range = last.high - last.low
    if bar_range <= 0:
        return None
    if (last.close - last.low) <= 0.3 * bar_range:
        return None
    pullback_low = min(b.low for b in bars5m[-3:])
    return EntrySignal(side=EntrySide.LONG, pullback_low_or_high=pullback_low)


def short_signal_v03(
    *,
    bars5m: list[Bar5m],
    ema50_60m: float | None,
    ema200_60m: float | None,
    close_60m: float | None,
    session_vwap_5m: list[float | None],
    atr14_5m: list[float | None],
) -> EntrySignal | None:
    _check_gate()
    if len(bars5m) < 3:
        return None
    if ema50_60m is None or ema200_60m is None or close_60m is None:
        return None
    if ema50_60m > ema200_60m and close_60m > ema200_60m:
        return None
    last = bars5m[-1]
    prev = bars5m[-2]
    vwap_last = session_vwap_5m[-1] if session_vwap_5m else None
    atr_last = atr14_5m[-1] if atr14_5m else None
    if vwap_last is None or atr_last is None:
        return None
    if not classify_extension_short(close=last.close, session_vwap=vwap_last, atr14=atr_last):
        return None
    if last.high >= prev.high:
        return None
    bar_range = last.high - last.low
    if bar_range <= 0:
        return None
    if (last.high - last.close) <= 0.3 * bar_range:
        return None
    pullback_high = max(b.high for b in bars5m[-3:])
    return EntrySignal(side=EntrySide.SHORT, pullback_low_or_high=pullback_high)


def plan_long_v03(
    *,
    pullback_low: int,
    current_ask: int,
    modeled_slippage_ticks: int,
    atr14: float,
    session_vwap: float,
    actual_entry_fill: int | None = None,
) -> StopTargetPlan:
    _check_gate()
    expected_entry = current_ask + modeled_slippage_ticks
    candidate_stop = pullback_low - 1
    candidate_R = expected_entry - candidate_stop
    candidate_target = math.floor(session_vwap / _TICK_SIZE) * _TICK_SIZE

    skip: str | None
    if candidate_R <= 0:
        skip = "candidate_R_non_positive"
    elif candidate_R > 1.5 * atr14:
        skip = "candidate_R_too_large"
    elif candidate_R < 0.5 * atr14:
        skip = "candidate_R_too_small"
    elif candidate_target - expected_entry < 0.5 * atr14:
        skip = "vwap_target_too_close"
    elif candidate_target <= expected_entry:
        skip = "vwap_target_below_entry"
    else:
        skip = None

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
    target = math.floor(session_vwap / _TICK_SIZE) * _TICK_SIZE
    if target <= actual_entry_fill:
        return StopTargetPlan(
            side=EntrySide.LONG,
            expected_entry=expected_entry,
            candidate_stop=candidate_stop,
            candidate_R=candidate_R,
            actual_R=actual_R,
            target=target,
            skip_reason="vwap_target_below_fill_error_halted",
        )
    return StopTargetPlan(
        side=EntrySide.LONG,
        expected_entry=expected_entry,
        candidate_stop=candidate_stop,
        candidate_R=candidate_R,
        actual_R=actual_R,
        target=target,
        skip_reason=None,
    )


def plan_short_v03(
    *,
    pullback_high: int,
    current_bid: int,
    modeled_slippage_ticks: int,
    atr14: float,
    session_vwap: float,
    actual_entry_fill: int | None = None,
) -> StopTargetPlan:
    _check_gate()
    expected_entry = current_bid - modeled_slippage_ticks
    candidate_stop = pullback_high + 1
    candidate_R = candidate_stop - expected_entry
    candidate_target = math.ceil(session_vwap / _TICK_SIZE) * _TICK_SIZE

    skip: str | None
    if candidate_R <= 0:
        skip = "candidate_R_non_positive"
    elif candidate_R > 1.5 * atr14:
        skip = "candidate_R_too_large"
    elif candidate_R < 0.5 * atr14:
        skip = "candidate_R_too_small"
    elif expected_entry - candidate_target < 0.5 * atr14:
        skip = "vwap_target_too_close"
    elif candidate_target >= expected_entry:
        skip = "vwap_target_above_entry"
    else:
        skip = None

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
    target = math.ceil(session_vwap / _TICK_SIZE) * _TICK_SIZE
    if target >= actual_entry_fill:
        return StopTargetPlan(
            side=EntrySide.SHORT,
            expected_entry=expected_entry,
            candidate_stop=candidate_stop,
            candidate_R=candidate_R,
            actual_R=actual_R,
            target=target,
            skip_reason="vwap_target_above_fill_error_halted",
        )
    return StopTargetPlan(
        side=EntrySide.SHORT,
        expected_entry=expected_entry,
        candidate_stop=candidate_stop,
        candidate_R=candidate_R,
        actual_R=actual_R,
        target=target,
        skip_reason=None,
    )
