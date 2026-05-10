"""NinjaScript-bridge broker adapter — refusing stub.

The Python codebase runs inside a Windows 11 VM (Parallels) alongside
the NinjaTrader 8 desktop. Orders flow:

    Python  ----TCP/JSON---->  AlgotradingBridge AddOn  ---->  NT8 desktop  ----> broker
            (127.0.0.1:<port>,    (NinjaScript C# AddOn,
             bearer token)         see tools/ninjascript_bridge/)

This adapter is the seam we will fill in once Appendix F is signed AND
the C# AddOn under ``tools/ninjascript_bridge/`` is implemented and
deployed. Until then every method raises :class:`BlockedLiveTrading`.

Same gate protocol as :class:`LiveBrokerAdapter`: every public method
runs the six-condition check from
``governance.phase_gates.assert_live_unblocked`` first, then refuses
because the implementation is intentionally absent.

Configuration is read from environment variables (never the repo). The
operator sets these on the Windows VM where Python runs:

  - ``NT_BRIDGE_HOST``   default ``127.0.0.1`` — the bridge MUST listen
    on loopback only; remote bridge access is a hard-no per Appendix F.
  - ``NT_BRIDGE_PORT``   integer; matches the AddOn's configured port.
  - ``NT_BRIDGE_TOKEN``  bearer token; must match the AddOn's token.
  - ``NT_BRIDGE_ACCOUNT`` NT account name to route orders to.
  - ``NT_BRIDGE_ENV`` ∈ {``sim``, ``live``} — ``sim`` points at NT's
    simulation account. ``live`` requires every other gate satisfied.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .interface import BrokerFill, BrokerOrder
from .live_adapter import BlockedLiveTrading, LiveBrokerAdapter


_REQUIRED_ENV_VARS: tuple[str, ...] = (
    "NT_BRIDGE_HOST",
    "NT_BRIDGE_PORT",
    "NT_BRIDGE_TOKEN",
    "NT_BRIDGE_ACCOUNT",
    "NT_BRIDGE_ENV",
)


@dataclass
class NinjaScriptBridgeAdapter(LiveBrokerAdapter):
    """Refusing-by-default NinjaScript-bridge adapter.

    Inherits the six gate-input flags from :class:`LiveBrokerAdapter`.
    Defaults remain unsafe; constructing without overrides will not
    unblock.

    Adds:
      - ``host`` / ``port`` — where the C# AddOn listens.
      - ``account`` — the NT account name (e.g., ``"Sim101"`` or your
        live account label).
      - ``env`` ∈ {``"sim"``, ``"live"``}.
    """

    host: str = "127.0.0.1"
    port: int = 0
    account: str = ""
    env: str = "sim"
    _token: str = ""
    _credentials: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(
        cls,
        repo_root: Path,
        **gate_overrides: bool,
    ) -> "NinjaScriptBridgeAdapter":
        """Construct from environment variables.

        Refuses on any missing or invalid value. ``NT_BRIDGE_HOST``
        outside the loopback range is rejected — the bridge must run
        on the same machine as NT8.
        """
        missing = [v for v in _REQUIRED_ENV_VARS if not os.environ.get(v)]
        if missing:
            raise BlockedLiveTrading(
                "BLOCKED_LIVE_TRADING: missing NinjaScript bridge environment "
                f"variables: {', '.join(missing)}. See "
                "docs/broker/ninjatrader_integration.md."
            )
        host = os.environ["NT_BRIDGE_HOST"]
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise BlockedLiveTrading(
                f"BLOCKED_LIVE_TRADING: NT_BRIDGE_HOST must be loopback "
                f"(127.0.0.1, localhost, or ::1); got {host!r}"
            )
        try:
            port = int(os.environ["NT_BRIDGE_PORT"])
        except ValueError as exc:
            raise BlockedLiveTrading(
                f"BLOCKED_LIVE_TRADING: NT_BRIDGE_PORT must be an integer: {exc}"
            ) from exc
        if not (1024 <= port <= 65535):
            raise BlockedLiveTrading(
                f"BLOCKED_LIVE_TRADING: NT_BRIDGE_PORT must be in 1024-65535, got {port}"
            )
        env = os.environ["NT_BRIDGE_ENV"]
        if env not in {"sim", "live"}:
            raise BlockedLiveTrading(
                f"BLOCKED_LIVE_TRADING: NT_BRIDGE_ENV must be 'sim' or 'live', got {env!r}"
            )
        return cls(
            repo_root=repo_root,
            host=host,
            port=port,
            account=os.environ["NT_BRIDGE_ACCOUNT"],
            env=env,
            _token=os.environ["NT_BRIDGE_TOKEN"],
            _credentials={v: os.environ[v] for v in _REQUIRED_ENV_VARS},
            **gate_overrides,
        )

    def base_url(self) -> str:
        return f"tcp://{self.host}:{self.port}"

    # ----- Public broker surface (all refusing) -----------------------------

    def submit(self, order: BrokerOrder) -> str:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: NinjaScript bridge submit() is not implemented; "
            "Appendix F sign-off plus the C# AddOn under "
            "tools/ninjascript_bridge/ are prerequisites."
        )

    def cancel(self, order_id: str) -> bool:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: NinjaScript bridge cancel() is not implemented"
        )

    def cancel_all(self) -> int:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: NinjaScript bridge cancel_all() is not implemented"
        )

    def positions(self) -> dict[str, int]:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: NinjaScript bridge positions() is not implemented"
        )

    def working_orders(self) -> list[BrokerOrder]:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: NinjaScript bridge working_orders() is not implemented"
        )

    def fills(self) -> list[BrokerFill]:
        self._gate()
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: NinjaScript bridge fills() is not implemented"
        )

    # ----- Implementation seams (deliberately not yet implemented) ----------
    #
    # When Appendix F is signed and the C# AddOn is deployed, the
    # public methods above will call into these. Each seam corresponds
    # to one JSON command on the bridge protocol; see
    # tools/ninjascript_bridge/README.md for the wire format.

    def _bridge_authenticate(self) -> None:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _bridge_authenticate() is a seam stub"
        )

    def _bridge_place_bracket(self, order: BrokerOrder) -> str:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _bridge_place_bracket() is a seam stub"
        )

    def _bridge_cancel(self, order_id: str) -> bool:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _bridge_cancel() is a seam stub"
        )

    def _bridge_reconcile(self) -> None:
        raise BlockedLiveTrading(
            "BLOCKED_LIVE_TRADING: _bridge_reconcile() is a seam stub"
        )
