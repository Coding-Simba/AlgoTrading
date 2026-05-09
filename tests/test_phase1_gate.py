"""Phase 1 sign-off gate tests.

Three contract checks for the v0.2_code gate:

1. Real-config canary: against the *real* `configs/` files in the repo,
   the three v0.2_code prerequisites (sign-off matrix B/C/D/E/H, risk
   limits, partition lock) are signed/locked. The validation-freeze
   guard remains BLOCKED because no `validation_freeze` event has been
   appended to the contamination log yet (that gate is the *next* one
   in sequence per docs/risk/validation_freeze_checklist.md). If any of
   the three prerequisites is silently flipped back, this canary fails
   loudly.

2. Signed-state allow: with fixture configs that mirror a fully-signed
   state plus a freeze event, all four guards return without raising.

3. Tamper canary: flipping a single appendix back to unsigned in the
   fixture re-blocks the gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from algotrading.contamination import (
    PartitionLockMissing,
    enforce_no_validation_before_freeze,
    is_partition_lock_signed,
)
from algotrading.governance import (
    SignoffError,
    assert_risk_limits_signed,
    assert_v02_code_unblocked,
    is_risk_limits_signed,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_REAL_SIGNOFF = _REPO_ROOT / "configs" / "signoff_matrix.yml"
_REAL_RISK = _REPO_ROOT / "configs" / "risk_limits.yml"
_REAL_PARTITIONS = _REPO_ROOT / "configs" / "data_partitions.yml"
_REAL_LOG = _REPO_ROOT / "docs" / "research_contamination_log" / "research_contamination_log.csv"


# ---------- 1. Real-config canary: signed for v0.2_code, freeze pending ----


def test_phase1_gate_real_configs_signed_for_v02_code_but_freeze_pending() -> None:
    assert _REAL_SIGNOFF.exists(), f"missing {_REAL_SIGNOFF}"
    assert _REAL_RISK.exists(), f"missing {_REAL_RISK}"
    assert _REAL_PARTITIONS.exists(), f"missing {_REAL_PARTITIONS}"

    # B/C/D/E/H signed → v0.2_code gate ALLOWS.
    assert_v02_code_unblocked(_REAL_SIGNOFF)

    # risk_limits.yml signed and locked.
    assert is_risk_limits_signed(_REAL_RISK)
    assert_risk_limits_signed(_REAL_RISK)

    # data_partitions.yml signed and locked.
    assert is_partition_lock_signed(_REAL_PARTITIONS)

    # Validation guard still BLOCKED — partition is locked, but no
    # validation_freeze event has been appended to the contamination
    # log yet. That is the next gate in sequence.
    with pytest.raises(PartitionLockMissing):
        enforce_no_validation_before_freeze(
            strategy_version="v0.2",
            partitions_path=_REAL_PARTITIONS,
            contamination_log_path=_REAL_LOG,
        )


# ---------- 2. Signed-state allow against fixture configs ------------------


_SIGNED_SIGNOFF = """\
rows:
  - id: "B"
    title: "Appendix B"
    signer_role: "Director sponsor"
    required_for: "v0.2_code"
    signed: true
    signed_by: "DIR-01"
    signed_at_iso: "2026-05-09T10:00:00-04:00"
    notes: ""
  - id: "C"
    title: "Appendix C"
    signer_role: "Risk reviewer"
    required_for: "v0.2_code"
    signed: true
    signed_by: "RISK-01"
    signed_at_iso: "2026-05-09T10:01:00-04:00"
    notes: ""
  - id: "D"
    title: "Appendix D"
    signer_role: "Engineering"
    required_for: "v0.2_code"
    signed: true
    signed_by: "ENG-01"
    signed_at_iso: "2026-05-09T10:02:00-04:00"
    notes: ""
  - id: "E"
    title: "Appendix E"
    signer_role: "Quant"
    required_for: "v0.2_code"
    signed: true
    signed_by: "QUANT-01"
    signed_at_iso: "2026-05-09T10:03:00-04:00"
    notes: ""
  - id: "H"
    title: "Appendix H"
    signer_role: "Engineering"
    required_for: "v0.2_code"
    signed: true
    signed_by: "ENG-01"
    signed_at_iso: "2026-05-09T10:04:00-04:00"
    notes: ""
"""


_SIGNED_RISK = """\
allocated_capital_usd: 100000
max_oos_drawdown_pct: 20
max_acceptable_losing_streak: 6
daily_loss_limit_usd: 2000
aggregate_program_drawdown_limit_pct: 25
risk_of_ruin_threshold_pct: 5
signed_by: "DIR-01"
signed_at_iso: "2026-05-09T10:00:00-04:00"
locked: true
"""


_SIGNED_PARTITIONS = """\
locked: true
locked_by: "DIR-01"
locked_at_iso: "2026-05-09T10:00:00-04:00"
partitions:
  training:       {start: '2022-01-03', end: '2024-12-31'}
  validation:     {start: '2025-01-02', end: '2025-12-31'}
  final_holdback: {start: '2026-01-02', end: '2026-04-30'}
"""


@pytest.fixture
def signed_world(tmp_path: Path) -> dict[str, Path]:
    signoff = tmp_path / "signoff_matrix.yml"
    signoff.write_text(_SIGNED_SIGNOFF, encoding="utf-8")
    risk = tmp_path / "risk_limits.yml"
    risk.write_text(_SIGNED_RISK, encoding="utf-8")
    partitions = tmp_path / "data_partitions.yml"
    partitions.write_text(_SIGNED_PARTITIONS, encoding="utf-8")
    log = tmp_path / "research_contamination_log.csv"
    from algotrading.contamination import ContaminationLog, LogRow
    cl = ContaminationLog(log)
    cl.append(
        LogRow(
            datetime_iso="2026-05-09T10:30:00-04:00",
            researcher="RISK-01",
            strategy_version="v0.2",
            action_type="other",
            description="validation_freeze: v0.2 partition lock signed; one-shot OOS authorised",
            dataset_used="none",
            result_observed="N/A",
            decision="kept",
        )
    )
    return {"signoff": signoff, "risk": risk, "partitions": partitions, "log": log}


def test_phase1_gate_allows_v02_code_when_signed(signed_world: dict[str, Path]) -> None:
    assert_v02_code_unblocked(signed_world["signoff"])

    assert is_risk_limits_signed(signed_world["risk"])
    assert_risk_limits_signed(signed_world["risk"])

    assert is_partition_lock_signed(signed_world["partitions"])
    enforce_no_validation_before_freeze(
        strategy_version="v0.2",
        partitions_path=signed_world["partitions"],
        contamination_log_path=signed_world["log"],
    )


def test_phase1_gate_blocks_when_one_appendix_unsigned(signed_world: dict[str, Path]) -> None:
    flipped = signed_world["signoff"].read_text(encoding="utf-8").replace(
        '    signed: true\n    signed_by: "ENG-01"\n    signed_at_iso: "2026-05-09T10:02:00-04:00"',
        '    signed: false\n    signed_by: ""\n    signed_at_iso: ""',
        1,
    )
    signed_world["signoff"].write_text(flipped, encoding="utf-8")
    with pytest.raises(SignoffError):
        assert_v02_code_unblocked(signed_world["signoff"])
