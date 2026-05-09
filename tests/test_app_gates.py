"""Gate-blocked tests for the runners and the live adapter.

These exercise the *real* configs in the repo. B/C/D/E/H + risk_limits +
partition lock are signed (v0.2_code ALLOWED). Every downstream
dangerous path (OOS, holdback, paper, live, scaleup) still refuses by
default because its own row remains unsigned. Synthetic paths must
remain runnable.
"""

from pathlib import Path

import pytest

from algotrading.broker import BlockedLiveTrading, LiveBrokerAdapter
from algotrading.broker.interface import BrokerOrder
from algotrading.governance.phase_gates import (
    GateBlocked,
    GateContext,
    assert_scaleup_unblocked,
    gate_summary,
)
from algotrading.research import HoldbackBlocked, HoldbackRunner, OOSBlocked, OOSRunner


_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_oos_blocked_against_unsigned_repo() -> None:
    runner = OOSRunner(_REPO_ROOT)
    with pytest.raises(OOSBlocked):
        runner.run(strategy_version="v0.2")


def test_holdback_blocked_against_unsigned_repo() -> None:
    runner = HoldbackRunner(_REPO_ROOT)
    with pytest.raises(HoldbackBlocked):
        runner.run(oos_pass_recorded=False, holdback_trade_count_threshold_met=False)


def test_holdback_blocked_even_with_oos_pass_if_threshold_unmet() -> None:
    runner = HoldbackRunner(_REPO_ROOT)
    with pytest.raises(HoldbackBlocked):
        runner.run(oos_pass_recorded=True, holdback_trade_count_threshold_met=False)


def test_live_adapter_refuses_by_default() -> None:
    adapter = LiveBrokerAdapter(repo_root=_REPO_ROOT)
    order = BrokerOrder(
        client_order_id="probe",
        symbol="MES",
        side="buy",
        qty=1,
        order_type="market",
        price=None,
    )
    with pytest.raises(BlockedLiveTrading):
        adapter.submit(order)


def test_live_adapter_refuses_even_with_explicit_flag_alone() -> None:
    """The flag alone is not enough; paper gate + broker confirms etc.
    must also be true."""
    adapter = LiveBrokerAdapter(
        repo_root=_REPO_ROOT,
        explicit_live_enable_flag=True,
    )
    with pytest.raises(BlockedLiveTrading):
        adapter._gate()  # noqa: SLF001


def test_scale_up_blocked_against_unsigned_repo() -> None:
    ctx = GateContext.default(_REPO_ROOT)
    with pytest.raises(GateBlocked):
        assert_scaleup_unblocked(ctx)


def test_gate_summary_v02_code_allowed_others_blocked() -> None:
    """B/C/D/E/H + risk_limits + partition lock are signed, so v0.2_code is
    ALLOWED. Every downstream gate (approved_backtest, oos, holdback, paper,
    live, scaleup) remains BLOCKED on its own row (broker_rate_sheet,
    validation_freeze, F, paper, G respectively)."""
    summary = gate_summary(GateContext.default(_REPO_ROOT))

    assert summary["v0.2_code"]["status"] == "ALLOWED", summary["v0.2_code"]
    for gate in ("approved_backtest", "oos", "holdback", "paper", "live", "scaleup"):
        assert gate in summary
        assert summary[gate]["status"] == "BLOCKED", f"{gate} should be blocked: {summary[gate]}"
