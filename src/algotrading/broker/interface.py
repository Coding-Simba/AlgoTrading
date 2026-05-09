"""Broker adapter interface.

The framework can target a mock broker (paper) or a live broker via the
same surface. Live adapters MUST refuse to trade unless every gate in
``governance.phase_gates.assert_live_unblocked`` passes; see
``live_adapter.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class BrokerOrder:
    client_order_id: str
    symbol: str
    side: str          # "buy" | "sell"
    qty: int
    order_type: str    # "market" | "limit" | "stop"
    price: int | None  # in ticks
    parent_id: str | None = None


@dataclass(frozen=True)
class BrokerFill:
    order_id: str
    symbol: str
    side: str
    qty: int
    price: int
    ts_ns: int
    cost_tag: str = ""


class BrokerAdapter(Protocol):
    def submit(self, order: BrokerOrder) -> str: ...
    def cancel(self, order_id: str) -> bool: ...
    def cancel_all(self) -> int: ...
    def positions(self) -> dict[str, int]: ...
    def working_orders(self) -> list[BrokerOrder]: ...
    def fills(self) -> list[BrokerFill]: ...
