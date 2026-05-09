"""Mock broker used by the paper simulator and synthetic E2E tests.

Implements the :class:`BrokerAdapter` protocol with in-memory order
book, OCO bracket support, latency simulation, and configurable
slippage. Carries the ``D2_PLACEHOLDER`` cost tag on every fill so the
governance gate refuses to mark any output as an approved backtest.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..broker.interface import BrokerFill, BrokerOrder
from ..fillmodel import D2_PLACEHOLDER_TAG


class MockBrokerError(RuntimeError):
    pass


@dataclass
class MockBroker:
    symbol: str = "MES"
    latency_ns: int = 1_000_000
    slippage_ticks: int = 1
    placeholder_costs: bool = True

    _id_counter: itertools.count = field(default_factory=lambda: itertools.count(1), init=False, repr=False)
    _working: dict[str, BrokerOrder] = field(default_factory=dict, init=False, repr=False)
    _oco_pairs: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _positions: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _fills: list[BrokerFill] = field(default_factory=list, init=False, repr=False)
    _last_ts_ns: int = field(default=0, init=False, repr=False)

    def _next_id(self) -> str:
        return f"MOCK-{next(self._id_counter)}"

    def _cost_tag(self) -> str:
        return D2_PLACEHOLDER_TAG if self.placeholder_costs else ""

    def submit(self, order: BrokerOrder) -> str:
        oid = self._next_id()
        self._working[oid] = order
        return oid

    def link_oco(self, a_id: str, b_id: str) -> None:
        if a_id not in self._working or b_id not in self._working:
            raise MockBrokerError("OCO link requires two working orders")
        self._oco_pairs[a_id] = b_id
        self._oco_pairs[b_id] = a_id

    def cancel(self, order_id: str) -> bool:
        return self._working.pop(order_id, None) is not None

    def cancel_all(self) -> int:
        n = len(self._working)
        self._working.clear()
        self._oco_pairs.clear()
        return n

    def positions(self) -> dict[str, int]:
        return dict(self._positions)

    def working_orders(self) -> list[BrokerOrder]:
        return list(self._working.values())

    def fills(self) -> list[BrokerFill]:
        return list(self._fills)

    def step_ts(self, ts_ns: int) -> None:
        self._last_ts_ns = max(ts_ns, self._last_ts_ns + self.latency_ns)

    def fill_market(self, order_id: str, ref_price: int) -> BrokerFill:
        order = self._working.pop(order_id, None)
        if order is None:
            raise MockBrokerError(f"unknown working order: {order_id}")
        slip = self.slippage_ticks if order.side == "buy" else -self.slippage_ticks
        px = ref_price + slip
        delta = order.qty if order.side == "buy" else -order.qty
        self._positions[order.symbol] = self._positions.get(order.symbol, 0) + delta
        fill = BrokerFill(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            price=px,
            ts_ns=self._last_ts_ns,
            cost_tag=self._cost_tag(),
        )
        self._fills.append(fill)
        sibling = self._oco_pairs.pop(order_id, None)
        if sibling is not None:
            self._oco_pairs.pop(sibling, None)
            self._working.pop(sibling, None)
        return fill

    def fill_at(self, order_id: str, price: int) -> BrokerFill:
        order = self._working.pop(order_id, None)
        if order is None:
            raise MockBrokerError(f"unknown working order: {order_id}")
        delta = order.qty if order.side == "buy" else -order.qty
        self._positions[order.symbol] = self._positions.get(order.symbol, 0) + delta
        fill = BrokerFill(
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            qty=order.qty,
            price=price,
            ts_ns=self._last_ts_ns,
            cost_tag=self._cost_tag(),
        )
        self._fills.append(fill)
        sibling = self._oco_pairs.pop(order_id, None)
        if sibling is not None:
            self._oco_pairs.pop(sibling, None)
            self._working.pop(sibling, None)
        return fill

    def reconcile(self) -> dict[str, int]:
        return {
            "working_orders": len(self._working),
            "positions": sum(abs(q) for q in self._positions.values()),
            "fills": len(self._fills),
        }
