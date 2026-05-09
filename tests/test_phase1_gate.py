"""Phase 1 sign-off canary.

This test pins the current unsigned state of the repo: while any of the five
pre-code sign-offs (Appendices B, C, D, E, H), the Director-set risk limits,
or the data-partition lock are blank, v0.2 strategy code must remain blocked.
The test passes today *because* the gates correctly refuse. If a future edit
silently flips a row to signed, this canary will start failing and force the
change to be reviewed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from algotrading.contamination import PartitionLockMissing, is_partition_lock_signed
from algotrading.governance import (
    RiskLimitsError,
    SignoffError,
    assert_risk_limits_signed,
    assert_v02_code_unblocked,
    is_risk_limits_signed,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SIGNOFF_PATH = _REPO_ROOT / "configs" / "signoff_matrix.yml"
_RISK_PATH = _REPO_ROOT / "configs" / "risk_limits.yml"
_PARTITIONS_PATH = _REPO_ROOT / "configs" / "data_partitions.yml"


def test_phase1_gate_blocks_v02_code() -> None:
    assert _SIGNOFF_PATH.exists(), f"missing {_SIGNOFF_PATH}"
    assert _RISK_PATH.exists(), f"missing {_RISK_PATH}"
    assert _PARTITIONS_PATH.exists(), f"missing {_PARTITIONS_PATH}"

    with pytest.raises(SignoffError):
        assert_v02_code_unblocked(_SIGNOFF_PATH)

    assert not is_risk_limits_signed(_RISK_PATH)
    with pytest.raises(RiskLimitsError):
        assert_risk_limits_signed(_RISK_PATH)

    assert not is_partition_lock_signed(_PARTITIONS_PATH)
    from algotrading.contamination import enforce_no_validation_before_freeze

    with pytest.raises(PartitionLockMissing):
        enforce_no_validation_before_freeze(
            strategy_version="v0.2",
            partitions_path=_PARTITIONS_PATH,
            contamination_log_path=_REPO_ROOT
            / "docs"
            / "research_contamination_log"
            / "research_contamination_log.csv",
        )
