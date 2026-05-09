"""Paper simulator (synthetic only).

Runs the v0.2 strategy against a list of synthetic 5m bars + 60m
context. Produces a structured run result the reporting module can
render. Never connects to a real broker; uses :class:`MockBroker`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timezone

from ..broker.interface import BrokerOrder
from ..fillmodel import D2_PLACEHOLDER_TAG
from ..orders import (
    DEFAULT_FLATTEN_SEQUENCE,
    ExecutionLifecycle,
    ExecutionState,
)
from ..strategy_v02 import (
    Bar5m,
    EntrySide,
    SessionCounters,
    TrendFilter60m,
    long_signal,
    plan_long,
    plan_short,
    short_signal,
)
from ..strategy_v02.notrade import NoTradeContext, blocking_reasons
from .mock_broker import MockBroker


@dataclass
class SyntheticBar:
    ts_ns: int
    et_time: time
    bar: Bar5m
    ema200_5m: float | None
    ema20_5m: float | None
    vwap_5m: float | None
    trend_60m: TrendFilter60m
    atr14_5m: float
    bid: int
    ask: int


@dataclass
class PaperRunResult:
    bars_processed: int = 0
    signals_seen: int = 0
    entries_taken: int = 0
    skips_due_to_atr_filter: int = 0
    skips_due_to_no_trade: int = 0
    fills: int = 0
    error_halted_count: int = 0
    placeholder_cost_fills: int = 0
    notes: list[str] = field(default_factory=list)


class PaperSimulator:
    def __init__(self, broker: MockBroker | None = None) -> None:
        self.broker = broker or MockBroker()
        self.lifecycle = ExecutionLifecycle()
        self.counters = SessionCounters()

    def _no_trade_ctx(self, sb: SyntheticBar) -> NoTradeContext:
        return NoTradeContext(
            et_time=sb.et_time,
            in_news_blackout=False,
            in_pre_news_flatten_window=False,
            spread_ticks=max(0, sb.ask - sb.bid),
            seconds_since_last_tick=0.0,
            bbo_present=True,
            book_locked_or_crossed=sb.bid > sb.ask,
            broker_degraded=False,
            exchange_halt=False,
            limit_up_down=False,
            clock_drift_ms=0.0,
            signal_calc_latency_s=0.0,
            signal_to_order_latency_s=0.0,
            osm_state=self.lifecycle.state.value.upper(),
            kill_switch_active=False,
        )

    def run(self, bars: list[SyntheticBar]) -> PaperRunResult:
        result = PaperRunResult()
        bars5m: list[Bar5m] = []
        ema200_series: list[float | None] = []
        ema20_series: list[float | None] = []
        vwap_series: list[float | None] = []

        for sb in bars:
            result.bars_processed += 1
            self.broker.step_ts(sb.ts_ns)

            bars5m.append(sb.bar)
            ema200_series.append(sb.ema200_5m)
            ema20_series.append(sb.ema20_5m)
            vwap_series.append(sb.vwap_5m)

            ctx = self._no_trade_ctx(sb)
            blockers = blocking_reasons(ctx)

            long = short = None
            if not blockers and self.counters.can_enter():
                long = long_signal(
                    bars5m=bars5m,
                    ema200_5m=ema200_series,
                    ema20_5m=ema20_series,
                    vwap_5m=vwap_series,
                    trend_60m=sb.trend_60m,
                )
                if long is None:
                    short = short_signal(
                        bars5m=bars5m,
                        ema200_5m=ema200_series,
                        ema20_5m=ema20_series,
                        vwap_5m=vwap_series,
                        trend_60m=sb.trend_60m,
                    )

            sig = long or short
            if sig is None:
                if blockers:
                    result.skips_due_to_no_trade += 1
                continue

            result.signals_seen += 1
            if sig.side is EntrySide.LONG:
                plan = plan_long(
                    pullback_low=sig.pullback_low_or_high,
                    current_ask=sb.ask,
                    modeled_slippage_ticks=self.broker.slippage_ticks,
                    atr14=sb.atr14_5m,
                )
            else:
                plan = plan_short(
                    pullback_high=sig.pullback_low_or_high,
                    current_bid=sb.bid,
                    modeled_slippage_ticks=self.broker.slippage_ticks,
                    atr14=sb.atr14_5m,
                )
            if plan.skip_reason is not None:
                result.skips_due_to_atr_filter += 1
                continue

            try:
                self.lifecycle.transition(sb.ts_ns, ExecutionState.SIGNAL_PENDING, reason="signal")
                self.lifecycle.transition(sb.ts_ns + 1, ExecutionState.ENTRY_SENT, reason="entry submitted")
            except Exception as exc:  # noqa: BLE001
                self.lifecycle.transition_to_error(sb.ts_ns + 2, reason=f"lifecycle: {exc}")
                result.error_halted_count += 1
                continue

            order = BrokerOrder(
                client_order_id=f"V02-{result.bars_processed}",
                symbol=self.broker.symbol,
                side="buy" if sig.side is EntrySide.LONG else "sell",
                qty=1,
                order_type="market",
                price=None,
            )
            oid = self.broker.submit(order)
            ref_price = sb.ask if sig.side is EntrySide.LONG else sb.bid
            fill = self.broker.fill_market(oid, ref_price)
            result.fills += 1
            if fill.cost_tag == D2_PLACEHOLDER_TAG:
                result.placeholder_cost_fills += 1

            try:
                self.lifecycle.transition(sb.ts_ns + 3, ExecutionState.ENTRY_FILLED, reason="filled")
                self.lifecycle.transition(sb.ts_ns + 4, ExecutionState.BRACKET_PENDING, reason="bracket sent")
                self.lifecycle.transition(sb.ts_ns + 5, ExecutionState.POSITION_PROTECTED, reason="bracket ack")
                self.lifecycle.transition(sb.ts_ns + 6, ExecutionState.EXIT_PENDING, reason="synthetic exit")
                self.lifecycle.transition(sb.ts_ns + 7, ExecutionState.FLAT_RECONCILING, reason="exit confirmed")
                self.lifecycle.transition(sb.ts_ns + 8, ExecutionState.FLAT, reason="reconciled")
            except Exception as exc:  # noqa: BLE001
                self.lifecycle.transition_to_error(sb.ts_ns + 9, reason=f"lifecycle: {exc}")
                result.error_halted_count += 1
                continue

            self.counters.on_entry()
            self.counters.on_exit()
            result.entries_taken += 1

        result.notes.append(
            f"flatten plan = {[s.value for s in DEFAULT_FLATTEN_SEQUENCE]}"
        )
        return result


def synthetic_bars(n: int = 60) -> list[SyntheticBar]:
    """Build a deterministic synthetic 5m bar series for E2E tests and CLI
    smoke tests. Pure-numeric, no real-data dependency."""
    out: list[SyntheticBar] = []
    base_ts = int(datetime(2026, 5, 11, 14, 35, tzinfo=timezone.utc).timestamp() * 1_000_000_000)
    price = 4500
    for i in range(n):
        ts = base_ts + i * 5 * 60 * 1_000_000_000
        et = time(10, 35) if i == 0 else time(min(10 + (i * 5) // 60, 15), (35 + i * 5) % 60)
        bar = Bar5m(high=price + 3, low=price - 2, close=price + (1 if i % 5 != 4 else -2))
        out.append(
            SyntheticBar(
                ts_ns=ts,
                et_time=et,
                bar=bar,
                ema200_5m=float(price - 1),
                ema20_5m=float(price - 2),
                vwap_5m=float(price - 1),
                trend_60m=TrendFilter60m(ema50=float(price), ema200=float(price - 5), close=float(price)),
                atr14_5m=4.0,
                bid=price - 1,
                ask=price + 1,
            )
        )
        price += 1 if i % 5 != 4 else -2
    return out
