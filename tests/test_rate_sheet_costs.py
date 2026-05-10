"""Loader and consistency tests for RateSheetCosts and the
NinjaScriptBridgeAdapter stub.

These guard the seam between the unsigned-by-default rate sheet config
and the cost model that consumes it. The adapter stub gets refusal
canaries so renaming the file or accidentally implementing it without
removing the stub raises immediately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from algotrading.broker import BlockedLiveTrading, NinjaScriptBridgeAdapter
from algotrading.broker.interface import BrokerOrder
from algotrading.fillmodel import (
    D2_PLACEHOLDER_TAG,
    RateSheetCosts,
    RateSheetError,
    is_rate_sheet_signed,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_REAL_RATE_SHEET = _REPO_ROOT / "configs" / "broker_rate_sheet.yml"


# ---------- Real-config canary --------------------------------------------


def test_real_rate_sheet_exists_and_is_unsigned_today() -> None:
    """The real config exists, parses as YAML, and is intentionally
    unsigned. Flipping it to signed without an Ops PR review forces
    this test to fail."""
    assert _REAL_RATE_SHEET.exists(), f"missing {_REAL_RATE_SHEET}"
    assert not is_rate_sheet_signed(_REAL_RATE_SHEET)
    with pytest.raises(RateSheetError, match="not signed"):
        RateSheetCosts.load(_REAL_RATE_SHEET, instrument="MES")


# ---------- Signed-state acceptance ---------------------------------------


_SIGNED_RATE_SHEET = """\
meta:
  broker: "NinjaTrader Brokerage"
  api_route: "NinjaScript localhost bridge"
  plan: "free"
  retrieved_at_iso: "2026-05-09"

instruments:
  MES:
    name: "Micro E-mini S&P 500"
    tick_size: 0.25
    tick_value_usd_cents: 125
    nt_commission_per_side_usd_cents: 39
    cme_exchange_fee_per_side_usd_cents: 37
    nfa_assessment_per_side_usd_cents: 2
    clearing_fee_per_side_usd_cents: 6
    routing_fee_per_side_usd_cents: 0
    all_in_per_side_usd_cents: 84
    all_in_round_trip_usd_cents: 168

slippage:
  ticks_per_side: 1

signed_by: "OPS-01"
signed_at_iso: "2026-05-09T10:00:00-04:00"
signed: true
"""


@pytest.fixture
def signed_rate_sheet(tmp_path: Path) -> Path:
    p = tmp_path / "broker_rate_sheet.yml"
    p.write_text(_SIGNED_RATE_SHEET, encoding="utf-8")
    return p


def test_rate_sheet_loads_and_emits_no_placeholder_tag(signed_rate_sheet: Path) -> None:
    assert is_rate_sheet_signed(signed_rate_sheet)
    rs = RateSheetCosts.load(signed_rate_sheet, instrument="MES")
    assert rs.tag != D2_PLACEHOLDER_TAG
    assert rs.tag == ""
    assert rs.commission_per_side_usd_cents == 39
    assert rs.all_in_per_side_usd_cents == 84
    # 84 cents / 125 cents-per-tick → ceil(0.672) = 1 tick (conservative).
    assert rs.commission_per_side_ticks == 1


def test_rate_sheet_rejects_when_components_dont_sum(tmp_path: Path) -> None:
    p = tmp_path / "rate.yml"
    bad = _SIGNED_RATE_SHEET.replace(
        "all_in_per_side_usd_cents: 84",
        "all_in_per_side_usd_cents: 90",  # off by 6.
    )
    p.write_text(bad, encoding="utf-8")
    with pytest.raises(RateSheetError, match="does not match"):
        RateSheetCosts.load(p, instrument="MES")


def test_rate_sheet_rejects_when_round_trip_not_double(tmp_path: Path) -> None:
    p = tmp_path / "rate.yml"
    bad = _SIGNED_RATE_SHEET.replace(
        "all_in_round_trip_usd_cents: 168",
        "all_in_round_trip_usd_cents: 170",  # not 2 × 84.
    )
    p.write_text(bad, encoding="utf-8")
    with pytest.raises(RateSheetError, match="round_trip"):
        RateSheetCosts.load(p, instrument="MES")


def test_rate_sheet_rejects_when_signed_by_blank(tmp_path: Path) -> None:
    p = tmp_path / "rate.yml"
    bad = _SIGNED_RATE_SHEET.replace('signed_by: "OPS-01"', 'signed_by: ""')
    p.write_text(bad, encoding="utf-8")
    with pytest.raises(RateSheetError, match="signed_by"):
        RateSheetCosts.load(p, instrument="MES")


def test_rate_sheet_rejects_unknown_instrument(signed_rate_sheet: Path) -> None:
    with pytest.raises(RateSheetError, match="MNQ"):
        RateSheetCosts.load(signed_rate_sheet, instrument="MNQ")


def test_is_rate_sheet_signed_handles_missing_file(tmp_path: Path) -> None:
    assert not is_rate_sheet_signed(tmp_path / "nope.yml")


# ---------- NinjaScript-bridge adapter stub canaries ----------------------


_BRIDGE_ENV_VARS = (
    "NT_BRIDGE_HOST",
    "NT_BRIDGE_PORT",
    "NT_BRIDGE_TOKEN",
    "NT_BRIDGE_ACCOUNT",
    "NT_BRIDGE_ENV",
)


def _set_valid_bridge_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NT_BRIDGE_HOST", "127.0.0.1")
    monkeypatch.setenv("NT_BRIDGE_PORT", "55555")
    monkeypatch.setenv("NT_BRIDGE_TOKEN", "x" * 64)
    monkeypatch.setenv("NT_BRIDGE_ACCOUNT", "Sim101")
    monkeypatch.setenv("NT_BRIDGE_ENV", "sim")


def test_bridge_adapter_refuses_submit_by_default() -> None:
    """submit() runs `_gate()` first, which fails because the paper-gate
    row is unsigned. That is the correct refusal order — even if every
    gate were satisfied, the adapter would still raise 'not implemented'
    afterward."""
    adapter = NinjaScriptBridgeAdapter(
        repo_root=_REPO_ROOT,
        host="127.0.0.1",
        port=55555,
        account="Sim101",
        env="sim",
    )
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


def test_bridge_adapter_refuses_even_with_explicit_flag_alone() -> None:
    adapter = NinjaScriptBridgeAdapter(
        repo_root=_REPO_ROOT,
        host="127.0.0.1",
        port=55555,
        account="Sim101",
        env="sim",
        explicit_live_enable_flag=True,
    )
    with pytest.raises(BlockedLiveTrading):
        adapter._gate()  # noqa: SLF001


def test_bridge_adapter_from_env_rejects_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for v in _BRIDGE_ENV_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(BlockedLiveTrading, match="missing NinjaScript bridge"):
        NinjaScriptBridgeAdapter.from_env(repo_root=_REPO_ROOT)


def test_bridge_adapter_from_env_rejects_non_loopback_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_valid_bridge_env(monkeypatch)
    monkeypatch.setenv("NT_BRIDGE_HOST", "10.0.0.5")
    with pytest.raises(BlockedLiveTrading, match="must be loopback"):
        NinjaScriptBridgeAdapter.from_env(repo_root=_REPO_ROOT)


def test_bridge_adapter_from_env_rejects_bad_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_valid_bridge_env(monkeypatch)
    monkeypatch.setenv("NT_BRIDGE_PORT", "80")  # privileged.
    with pytest.raises(BlockedLiveTrading, match="1024-65535"):
        NinjaScriptBridgeAdapter.from_env(repo_root=_REPO_ROOT)


def test_bridge_adapter_from_env_rejects_non_integer_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_valid_bridge_env(monkeypatch)
    monkeypatch.setenv("NT_BRIDGE_PORT", "not-a-number")
    with pytest.raises(BlockedLiveTrading, match="must be an integer"):
        NinjaScriptBridgeAdapter.from_env(repo_root=_REPO_ROOT)


def test_bridge_adapter_from_env_rejects_bad_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_valid_bridge_env(monkeypatch)
    monkeypatch.setenv("NT_BRIDGE_ENV", "production")
    with pytest.raises(BlockedLiveTrading, match="must be 'sim' or 'live'"):
        NinjaScriptBridgeAdapter.from_env(repo_root=_REPO_ROOT)


def test_bridge_adapter_from_env_loopback_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_valid_bridge_env(monkeypatch)
    adapter = NinjaScriptBridgeAdapter.from_env(repo_root=_REPO_ROOT)
    assert adapter.base_url() == "tcp://127.0.0.1:55555"
    assert adapter.account == "Sim101"
    assert adapter.env == "sim"
