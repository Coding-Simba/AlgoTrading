from datetime import time


from algotrading.strategy_v02 import (
    Bar5m,
    EntrySide,
    NoTradeContext,
    NoTradeReason,
    SessionCounters,
    TrendFilter60m,
    blocking_reasons,
    long_signal,
    plan_long,
    plan_short,
    round_to_tick,
    short_signal,
)


def _ema_series(value: float, n: int) -> list[float | None]:
    return [value] * n


def _vwap_series(value: float, n: int) -> list[float | None]:
    return [value] * n


def _trend_long_aligned() -> TrendFilter60m:
    return TrendFilter60m(ema50=4500.0, ema200=4490.0, close=4501.0)


def _trend_short_aligned() -> TrendFilter60m:
    return TrendFilter60m(ema50=4490.0, ema200=4500.0, close=4489.0)


def test_long_signal_full_flow() -> None:
    bars = [
        Bar5m(high=4500, low=4498, close=4499),
        Bar5m(high=4501, low=4495, close=4496),
        Bar5m(high=4502, low=4498, close=4500),
        Bar5m(high=4504, low=4499, close=4503),
    ]
    sig = long_signal(
        bars5m=bars,
        ema200_5m=_ema_series(4490.0, 4),
        ema20_5m=_ema_series(4496.0, 4),
        vwap_5m=_vwap_series(4496.0, 4),
        trend_60m=_trend_long_aligned(),
    )
    assert sig is not None
    assert sig.side is EntrySide.LONG
    assert sig.pullback_low_or_high == 4495


def test_long_signal_blocked_by_trend_filter() -> None:
    bars = [
        Bar5m(high=4500, low=4498, close=4499),
        Bar5m(high=4501, low=4495, close=4496),
        Bar5m(high=4502, low=4498, close=4500),
        Bar5m(high=4504, low=4499, close=4503),
    ]
    sig = long_signal(
        bars5m=bars,
        ema200_5m=_ema_series(4490.0, 4),
        ema20_5m=_ema_series(4496.0, 4),
        vwap_5m=_vwap_series(4496.0, 4),
        trend_60m=_trend_short_aligned(),
    )
    assert sig is None


def test_long_signal_blocked_no_continuation() -> None:
    bars = [
        Bar5m(high=4500, low=4498, close=4499),
        Bar5m(high=4501, low=4495, close=4496),
        Bar5m(high=4505, low=4498, close=4500),
        Bar5m(high=4504, low=4499, close=4503),
    ]
    sig = long_signal(
        bars5m=bars,
        ema200_5m=_ema_series(4490.0, 4),
        ema20_5m=_ema_series(4496.0, 4),
        vwap_5m=_vwap_series(4496.0, 4),
        trend_60m=_trend_long_aligned(),
    )
    assert sig is None


def test_short_signal_mirror() -> None:
    bars = [
        Bar5m(high=4502, low=4500, close=4501),
        Bar5m(high=4505, low=4499, close=4504),
        Bar5m(high=4502, low=4498, close=4499),
        Bar5m(high=4498, low=4495, close=4496),
    ]
    sig = short_signal(
        bars5m=bars,
        ema200_5m=_ema_series(4510.0, 4),
        ema20_5m=_ema_series(4504.0, 4),
        vwap_5m=_vwap_series(4504.0, 4),
        trend_60m=_trend_short_aligned(),
    )
    assert sig is not None
    assert sig.side is EntrySide.SHORT
    assert sig.pullback_low_or_high == 4505


def test_round_to_tick_long_floors_short_ceils() -> None:
    assert round_to_tick(100.7, EntrySide.LONG) == 100
    assert round_to_tick(100.3, EntrySide.SHORT) == 101


def test_plan_long_skip_when_R_too_large() -> None:
    plan = plan_long(
        pullback_low=4490,
        current_ask=4500,
        modeled_slippage_ticks=1,
        atr14=4.0,
    )
    assert plan.skip_reason == "candidate_R_too_large"


def test_plan_long_skip_when_R_too_small() -> None:
    plan = plan_long(
        pullback_low=4499,
        current_ask=4500,
        modeled_slippage_ticks=1,
        atr14=10.0,
    )
    assert plan.skip_reason == "candidate_R_too_small"


def test_plan_long_actual_R_and_target_rounding() -> None:
    plan = plan_long(
        pullback_low=4495,
        current_ask=4500,
        modeled_slippage_ticks=1,
        atr14=8.0,
        actual_entry_fill=4501,
    )
    assert plan.actual_R == 7
    assert plan.target == 4511
    assert plan.skip_reason is None


def test_plan_short_actual_R_and_target_rounding() -> None:
    plan = plan_short(
        pullback_high=4505,
        current_bid=4500,
        modeled_slippage_ticks=1,
        atr14=8.0,
        actual_entry_fill=4499,
    )
    assert plan.actual_R == 7
    assert plan.target == 4489


def test_plan_long_actual_R_non_positive_error_halted() -> None:
    plan = plan_long(
        pullback_low=4495,
        current_ask=4500,
        modeled_slippage_ticks=1,
        atr14=8.0,
        actual_entry_fill=4493,
    )
    assert plan.skip_reason == "actual_R_non_positive_error_halted"


def test_no_trade_outside_window() -> None:
    ctx = NoTradeContext(et_time=time(9, 31))
    reasons = blocking_reasons(ctx)
    assert NoTradeReason.OUTSIDE_SIGNAL_WINDOW in reasons


def test_no_trade_spread_too_wide() -> None:
    ctx = NoTradeContext(et_time=time(11, 0), spread_ticks=3)
    reasons = blocking_reasons(ctx)
    assert NoTradeReason.SPREAD_TOO_WIDE in reasons


def test_no_trade_clock_drift_over_250ms() -> None:
    ctx = NoTradeContext(et_time=time(11, 0), clock_drift_ms=251.0)
    reasons = blocking_reasons(ctx)
    assert NoTradeReason.CLOCK_DRIFT_OVER_250MS in reasons


def test_session_counters_max_3_one_open() -> None:
    c = SessionCounters()
    assert c.can_enter()
    for _ in range(3):
        c.on_entry()
        c.on_exit()
    assert not c.can_enter()


def test_session_counters_one_open_position() -> None:
    c = SessionCounters()
    c.on_entry()
    assert not c.can_enter()
    c.on_exit()
    assert c.can_enter()


def test_pre_news_flatten_blocks() -> None:
    ctx = NoTradeContext(et_time=time(11, 0), in_pre_news_flatten_window=True)
    assert NoTradeReason.PRE_NEWS_FLATTEN in blocking_reasons(ctx)


def test_15_58_outside_window_blocks() -> None:
    ctx = NoTradeContext(et_time=time(15, 58))
    assert NoTradeReason.OUTSIDE_SIGNAL_WINDOW in blocking_reasons(ctx)
