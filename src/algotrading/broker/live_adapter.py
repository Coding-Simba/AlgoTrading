"""Live broker adapter — safety stub.

This file ships **without** a real broker integration. Every public
method raises :class:`BlockedLiveTrading` unless every condition listed
in ``governance.phase_gates.assert_live_unblocked`` is satisfied. There
is no real order placement code path under v0.2.

Construction requires explicit values for every gate input. The default
constructor values are all unsafe (False / missing), and instantiation
without explicit overrides will not unblock.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..governance.phase_gates import (
    GateBlocked,
    GateContext,
    assert_live_unblocked,
)
from .interface import BrokerFill, BrokerOrder


class BlockedLiveTrading(GateBlocked):
    """Specific subclass so callers can grep for `BLOCKED_LIVE_TRADING`."""


@dataclass
class LiveBrokerAdapter:
    repo_root: Path
    broker_oco_confirmed: bool = False
    broker_costs_inserted: bool = False
    appendix_f_runbook_complete: bool = False
    account_controls_configured: bool = False
    max_order_size_one_mes: bool = True
    explicit_live_enable_flag: bool = False

    def _gate(self) -> None:
        ctx = GateContext.default(self.repo_root)
        try:
            assert_live_unblocked(
                ctx,
                broker_oco_confirmed=self.broker_oco_confirmed,
                broker_costs_inserted=self.broker_costs_inserted,
                appendix_f_runbook_complete=self.appendix_f_runbook_complete,
                account_controls_configured=self.account_controls_configured,
                max_order_size_one_mes=self.max_order_size_one_mes,
                explicit_live_enable_flag=self.explicit_live_enable_flag,
            )
        except GateBlocked as exc:
            raise BlockedLiveTrading(f"BLOCKED_LIVE_TRADING: {exc}") from exc

    def submit(self, order: BrokerOrder) -> str:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: live order placement is not implemented in v0.2; "
            "this adapter is a safety stub. Use the paper simulator for synthetic runs."
        )

    def cancel(self, order_id: str) -> bool:
        self._gate()
        raise BlockedLiveTrading("BLOCKED_LIVE_TRADING: live cancel not implemented")

    def cancel_all(self) -> int:
        self._gate()
        raise BlockedLiveTrading("BLOCKED_LIVE_TRADING: live cancel_all not implemented")

    def positions(self) -> dict[str, int]:
        self._gate()
        raise BlockedLiveTrading("BLOCKED_LIVE_TRADING: live positions not implemented")

    def working_orders(self) -> list[BrokerOrder]:
        self._gate()
        raise BlockedLiveTrading("BLOCKED_LIVE_TRADING: live working_orders not implemented")

    def fills(self) -> list[BrokerFill]:
        self._gate()
        raise BlockedLiveTrading("BLOCKED_LIVE_TRADING: live fills not implemented")
