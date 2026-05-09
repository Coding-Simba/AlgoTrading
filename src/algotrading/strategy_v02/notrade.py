"""No-trade conditions per Appendix B §B.8.

Each condition is a falsifiable predicate. ``blocking_reasons`` returns
the list of conditions currently active; an empty list means trading is
permitted (subject to entry-rule checks elsewhere).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from enum import Enum


class NoTradeReason(str, Enum):
    OUTSIDE_SIGNAL_WINDOW = "outside_signal_window"
    NEWS_BLACKOUT = "inside_news_blackout"
    PRE_NEWS_FLATTEN = "pre_news_flatten_window"
    SPREAD_TOO_WIDE = "bid_ask_spread_gt_2_ticks"
    STALE_TICK = "latest_tick_older_than_3s"
    MISSING_BBO = "missing_bbo"
    LOCKED_OR_CROSSED_BOOK = "locked_or_crossed_book"
    BROKER_DEGRADED = "broker_connection_degraded"
    EXCHANGE_HALT = "exchange_halt"
    LIMIT_UP_DOWN = "limit_up_or_down"
    CLOCK_DRIFT_OVER_250MS = "clock_drift_over_250ms"
    SIGNAL_LATENCY_OVER_2S = "signal_calculation_latency_over_2s"
    ORDER_LATENCY_OVER_3S = "signal_to_order_submission_latency_over_3s"
    OSM_NOT_FLAT = "order_state_machine_not_flat"
    KILL_SWITCH_ACTIVE = "operational_kill_switch_active"


@dataclass
class NoTradeContext:
    et_time: time
    in_news_blackout: bool = False
    in_pre_news_flatten_window: bool = False
    spread_ticks: int = 0
    seconds_since_last_tick: float = 0.0
    bbo_present: bool = True
    book_locked_or_crossed: bool = False
    broker_degraded: bool = False
    exchange_halt: bool = False
    limit_up_down: bool = False
    clock_drift_ms: float = 0.0
    signal_calc_latency_s: float = 0.0
    signal_to_order_latency_s: float = 0.0
    osm_state: str = "FLAT"
    kill_switch_active: bool = False


_SIGNAL_WINDOW_OPEN = time(10, 35)
_SIGNAL_WINDOW_CLOSE = time(15, 30)


def _outside_signal_window(t: time) -> bool:
    return t < _SIGNAL_WINDOW_OPEN or t > _SIGNAL_WINDOW_CLOSE


def blocking_reasons(ctx: NoTradeContext) -> list[NoTradeReason]:
    out: list[NoTradeReason] = []
    if _outside_signal_window(ctx.et_time):
        out.append(NoTradeReason.OUTSIDE_SIGNAL_WINDOW)
    if ctx.in_news_blackout:
        out.append(NoTradeReason.NEWS_BLACKOUT)
    if ctx.in_pre_news_flatten_window:
        out.append(NoTradeReason.PRE_NEWS_FLATTEN)
    if ctx.spread_ticks > 2:
        out.append(NoTradeReason.SPREAD_TOO_WIDE)
    if ctx.seconds_since_last_tick > 3:
        out.append(NoTradeReason.STALE_TICK)
    if not ctx.bbo_present:
        out.append(NoTradeReason.MISSING_BBO)
    if ctx.book_locked_or_crossed:
        out.append(NoTradeReason.LOCKED_OR_CROSSED_BOOK)
    if ctx.broker_degraded:
        out.append(NoTradeReason.BROKER_DEGRADED)
    if ctx.exchange_halt:
        out.append(NoTradeReason.EXCHANGE_HALT)
    if ctx.limit_up_down:
        out.append(NoTradeReason.LIMIT_UP_DOWN)
    if ctx.clock_drift_ms > 250:
        out.append(NoTradeReason.CLOCK_DRIFT_OVER_250MS)
    if ctx.signal_calc_latency_s > 2:
        out.append(NoTradeReason.SIGNAL_LATENCY_OVER_2S)
    if ctx.signal_to_order_latency_s > 3:
        out.append(NoTradeReason.ORDER_LATENCY_OVER_3S)
    if ctx.osm_state != "flat" and ctx.osm_state != "FLAT":
        out.append(NoTradeReason.OSM_NOT_FLAT)
    if ctx.kill_switch_active:
        out.append(NoTradeReason.KILL_SWITCH_ACTIVE)
    return out
