"""Fill model for unit-test scaffolding (per Appendix D).

Implements:

- Market, limit, and stop order fills against a tick stream.
- Stop trigger semantics: conservative OR of trade-tape print-through and
  BBO quote touch through the stop. A BUY stop triggers if last_trade >=
  stop OR ask >= stop; a SELL stop triggers if last_trade <= stop OR
  bid <= stop. The quote leg is optional (callers may pass quote=None for
  trade-only contexts), but real ingestion is expected to supply both.
- Intrabar collision: when both stop-loss and take-profit are reached
  within the same bar and the underlying ticks cannot disambiguate
  ordering, the model records the worst-case (stop-loss) outcome and
  flags the result as ambiguous.

Costs are deliberately placeholder values until the broker rate sheet
arrives (errata §5). The constant ``D2_PLACEHOLDER_TAG`` is embedded in any
output that uses placeholder costs so CI can refuse approved backtests that
still carry it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ..bars import Bar
from ..ingestion.types import BBOQuote, Tick


D2_PLACEHOLDER_TAG = "D2_PLACEHOLDER"


class FillModelError(RuntimeError):
    pass


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


@dataclass(frozen=True, slots=True)
class OrderIntent:
    side: OrderSide
    qty: int
    type: OrderType
    price: int | None = None
    stop_loss: int | None = None
    take_profit: int | None = None

    def __post_init__(self) -> None:
        if self.qty <= 0:
            raise FillModelError(f"qty must be positive, got {self.qty}")
        if self.type in (OrderType.LIMIT, OrderType.STOP) and self.price is None:
            raise FillModelError(f"price required for {self.type}")


@dataclass
class PlaceholderCosts:
    """Placeholder costs per §D.2. NOT for approved backtests (errata §5)."""

    commission_per_side_ticks: int = 1
    slippage_ticks: int = 1
    tag: str = D2_PLACEHOLDER_TAG


@dataclass
class FillResult:
    filled: bool
    fill_price: int | None
    fill_ts_ns: int | None
    qty: int
    cost_ticks: int
    notes: list[str] = field(default_factory=list)
    ambiguous_collision: bool = False
    cost_tag: str = ""

    def is_placeholder(self) -> bool:
        return self.cost_tag == D2_PLACEHOLDER_TAG


class FillModel:
    def __init__(self, costs: PlaceholderCosts | None = PlaceholderCosts()) -> None:
        self.costs = costs

    def fill_market(self, intent: OrderIntent, tick: Tick) -> FillResult:
        if intent.type is not OrderType.MARKET:
            raise FillModelError("fill_market requires OrderType.MARKET")
        slip = self._slip(intent.side)
        px = tick.price + slip
        return self._make_result(True, px, tick.ts_ns, intent.qty, ["market"])

    def fill_limit_on_tick(self, intent: OrderIntent, tick: Tick) -> FillResult | None:
        if intent.type is not OrderType.LIMIT:
            raise FillModelError("fill_limit_on_tick requires OrderType.LIMIT")
        assert intent.price is not None
        if intent.side is OrderSide.BUY and tick.price <= intent.price:
            return self._make_result(True, intent.price, tick.ts_ns, intent.qty, ["limit"])
        if intent.side is OrderSide.SELL and tick.price >= intent.price:
            return self._make_result(True, intent.price, tick.ts_ns, intent.qty, ["limit"])
        return None

    def stop_triggered(
        self, intent: OrderIntent, tick: Tick, quote: BBOQuote | None = None
    ) -> bool:
        """Conservative stop trigger: OR of trade-tape print-through and
        BBO quote touch through the stop, per signed spec.

        - BUY stop (covers a short): trigger if last_trade >= stop OR
          ask >= stop.
        - SELL stop (covers a long): trigger if last_trade <= stop OR
          bid <= stop.

        ``quote`` is optional: if not supplied, only the trade-tape leg is
        evaluated. Real ingestion is expected to supply both via the merged
        tick / BBO stream.
        """
        if intent.type is not OrderType.STOP:
            raise FillModelError("stop_triggered requires OrderType.STOP")
        assert intent.price is not None
        if intent.side is OrderSide.BUY:
            if tick.price >= intent.price:
                return True
            if quote is not None and quote.ask_px >= intent.price:
                return True
            return False
        # SELL
        if tick.price <= intent.price:
            return True
        if quote is not None and quote.bid_px <= intent.price:
            return True
        return False

    def fill_stop_on_tick(
        self,
        intent: OrderIntent,
        tick: Tick,
        quote: BBOQuote | None = None,
    ) -> FillResult | None:
        if not self.stop_triggered(intent, tick, quote=quote):
            return None
        slip = self._slip(intent.side)
        px = tick.price + slip
        return self._make_result(True, px, tick.ts_ns, intent.qty, ["stop_triggered"])

    def resolve_bracket_on_bar(
        self,
        side: OrderSide,
        qty: int,
        stop_loss: int,
        take_profit: int,
        bar: Bar,
    ) -> FillResult:
        hit_target = (
            (side is OrderSide.BUY and bar.high >= take_profit)
            or (side is OrderSide.SELL and bar.low <= take_profit)
        )
        hit_stop = (
            (side is OrderSide.BUY and bar.low <= stop_loss)
            or (side is OrderSide.SELL and bar.high >= stop_loss)
        )

        if hit_target and hit_stop:
            res = self._make_result(
                True, stop_loss, bar.close_ns, qty, ["bracket", "ambiguous_collision"]
            )
            res.ambiguous_collision = True
            return res
        if hit_target:
            return self._make_result(True, take_profit, bar.close_ns, qty, ["bracket_target"])
        if hit_stop:
            return self._make_result(True, stop_loss, bar.close_ns, qty, ["bracket_stop"])
        return FillResult(
            filled=False,
            fill_price=None,
            fill_ts_ns=None,
            qty=0,
            cost_ticks=0,
            notes=["bracket_pending"],
        )

    def _slip(self, side: OrderSide) -> int:
        if self.costs is None:
            return 0
        return self.costs.slippage_ticks if side is OrderSide.BUY else -self.costs.slippage_ticks

    def _make_result(
        self,
        filled: bool,
        fill_price: int | None,
        fill_ts_ns: int | None,
        qty: int,
        notes: list[str],
    ) -> FillResult:
        cost = 0
        tag = ""
        if self.costs is not None:
            cost = self.costs.commission_per_side_ticks
            tag = self.costs.tag
        return FillResult(
            filled=filled,
            fill_price=fill_price,
            fill_ts_ns=fill_ts_ns,
            qty=qty,
            cost_ticks=cost,
            notes=list(notes),
            cost_tag=tag,
        )
