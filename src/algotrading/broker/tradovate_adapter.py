"""Tradovate broker adapter — refusing stub.

Tradovate (a NinjaTrader Group platform) is the order-routing API used
by NinjaTrader Brokerage. This adapter is the seam we will fill in once
Appendix F is signed. Until then every method raises
:class:`BlockedLiveTrading` with a clear "Appendix F not signed" message.

Design context lives in `docs/broker/ninjatrader_integration.md`. The
adapter follows the same gate protocol as
:class:`algotrading.broker.live_adapter.LiveBrokerAdapter`: every call
runs the six-condition check from
``governance.phase_gates.assert_live_unblocked`` first, then refuses
because the implementation is intentionally absent.

The stub is structured so the eventual implementation only needs to
fill in the four `_tradovate_*` private methods. The public
:class:`BrokerAdapter` Protocol surface above does not change.

Credentials are read from the operator's environment. They are NOT
stored in the repo. See the runbook in
`docs/broker/ninjatrader_integration.md` for the variable list.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .interface import BrokerFill, BrokerOrder
from .live_adapter import BlockedLiveTrading, LiveBrokerAdapter


_REQUIRED_ENV_VARS: tuple[str, ...] = (
    "TRADOVATE_CLIENT_ID",
    "TRADOVATE_CLIENT_SECRET",
    "TRADOVATE_USERNAME",
    "TRADOVATE_PASSWORD",
    "TRADOVATE_APP_NAME",
    "TRADOVATE_ENV",
)


_DEMO_BASE_URL = "https://demo.tradovateapi.com/v1"
_LIVE_BASE_URL = "https://live.tradovateapi.com/v1"


@dataclass
class TradovateAdapter(LiveBrokerAdapter):
    """Refusing-by-default Tradovate adapter.

    Inherits the six gate-input flags from :class:`LiveBrokerAdapter`.
    All defaults remain unsafe; constructing this without overrides
    will not unblock.

    Adds:
      - ``env``: which Tradovate environment to point at when the
        eventual implementation lands. ``"demo"`` is the only value
        callable today; ``"live"`` is also accepted but the methods
        still refuse until Appendix F is signed.
    """

    env: str = "demo"
    _credentials: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, repo_root: Path, **gate_overrides: bool) -> "TradovateAdapter":
        """Construct an adapter from environment variables.

        Reads the six ``TRADOVATE_*`` variables documented in
        ``docs/broker/ninjatrader_integration.md`` and stashes them on
        the instance. Refuses construction if any are missing — even
        though the adapter itself refuses every call, missing
        credentials should fail loud at startup rather than at the
        first order.
        """
        missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
        if missing:
            raise BlockedLiveTrading(
                "BLOCKED_LIVE_TRADING: missing Tradovate environment "
                f"variables: {', '.join(missing)}. See "
                "docs/broker/ninjatrader_integration.md."
            )
        env = os.environ["TRADOVATE_ENV"]
        if env not in {"demo", "live"}:
            raise BlockedLiveTrading(
                f"BLOCKED_LIVE_TRADING: TRADOVATE_ENV must be 'demo' or 'live', got {env!r}"
            )
        return cls(
            repo_root=repo_root,
            env=env,
            _credentials={v: os.environ[v] for v in _REQUIRED_ENV_VARS},
            **gate_overrides,
        )

    def base_url(self) -> str:
        return _LIVE_BASE_URL if self.env == "live" else _DEMO_BASE_URL

    # ----- Public broker surface (all refusing) -----------------------------

    def submit(self, order: BrokerOrder) -> str:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: Tradovate submit() is not implemented; "
            "Appendix F sign-off and the operator runbook in "
            "docs/broker/ninjatrader_integration.md are prerequisites."
        )

    def cancel(self, order_id: str) -> bool:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: Tradovate cancel() is not implemented"
        )

    def cancel_all(self) -> int:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: Tradovate cancel_all() is not implemented"
        )

    def positions(self) -> dict[str, int]:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: Tradovate positions() is not implemented"
        )

    def working_orders(self) -> list[BrokerOrder]:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: Tradovate working_orders() is not implemented"
        )

    def fills(self) -> list[BrokerFill]:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: Tradovate fills() is not implemented"
        )

    # ----- Implementation seams (deliberately not yet implemented) ----------
    #
    # When Appendix F is signed and this stub is replaced with real
    # code, the public methods above should call into these. Keeping
    # the seams separate means the gate-refusal pattern is preserved
    # across the boundary: the public methods always run `_gate()`
    # first, and the private methods own the network calls.

    def _tradovate_authenticate(self) -> str:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _tradovate_authenticate() is a seam stub"
        )

    def _tradovate_place_oso(self, order: BrokerOrder) -> str:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _tradovate_place_oso() is a seam stub"
        )

    def _tradovate_cancel(self, order_id: str) -> bool:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _tradovate_cancel() is a seam stub"
        )

    def _tradovate_reconcile(self) -> None:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _tradovate_reconcile() is a seam stub"
        )
