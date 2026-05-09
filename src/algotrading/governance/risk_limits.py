"""Director-set risk limits loader and gate-blocking guard.

The Director Sponsor is the sole signer for the seven values in
``configs/risk_limits.yml``. The Risk Reviewer must be a different person
(see docs/OWNERS.md). The guard refuses by default: missing values,
out-of-range values, an unset signer, or ``locked: false`` all block
downstream gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml


class RiskLimitsError(RuntimeError):
    """Raised when risk limits are missing, malformed, or unsigned."""


@dataclass(frozen=True)
class RiskLimits:
    allocated_capital_usd: float | None
    max_oos_drawdown_pct: float | None
    max_acceptable_losing_streak: int | None
    daily_loss_limit_usd: float | None
    aggregate_program_drawdown_limit_pct: float | None
    risk_of_ruin_threshold_pct: float | None
    signed_by: str
    signed_at_iso: str
    locked: bool


def _coerce_number(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _coerce_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def load_risk_limits(path: str | Path) -> RiskLimits:
    p = Path(path)
    if not p.exists():
        raise RiskLimitsError(f"risk limits file not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RiskLimitsError(f"risk limits root must be a mapping: {p}")
    return RiskLimits(
        allocated_capital_usd=_coerce_number(raw.get("allocated_capital_usd")),
        max_oos_drawdown_pct=_coerce_number(raw.get("max_oos_drawdown_pct")),
        max_acceptable_losing_streak=_coerce_int(raw.get("max_acceptable_losing_streak")),
        daily_loss_limit_usd=_coerce_number(raw.get("daily_loss_limit_usd")),
        aggregate_program_drawdown_limit_pct=_coerce_number(
            raw.get("aggregate_program_drawdown_limit_pct")
        ),
        risk_of_ruin_threshold_pct=_coerce_number(raw.get("risk_of_ruin_threshold_pct")),
        signed_by=str(raw.get("signed_by") or ""),
        signed_at_iso=str(raw.get("signed_at_iso") or ""),
        locked=bool(raw.get("locked", False)),
    )


def _is_iso8601(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validation_errors(limits: RiskLimits) -> list[str]:
    errors: list[str] = []
    if not limits.locked:
        errors.append("locked is false")
    if not limits.signed_by.strip():
        errors.append("signed_by is empty")
    if not _is_iso8601(limits.signed_at_iso):
        errors.append("signed_at_iso is not ISO-8601")

    if limits.allocated_capital_usd is None:
        errors.append("allocated_capital_usd is missing")
    elif limits.allocated_capital_usd <= 0:
        errors.append("allocated_capital_usd must be > 0")

    if limits.max_oos_drawdown_pct is None:
        errors.append("max_oos_drawdown_pct is missing")
    elif not (0 < limits.max_oos_drawdown_pct < 100):
        errors.append("max_oos_drawdown_pct must be in (0, 100)")

    if limits.max_acceptable_losing_streak is None:
        errors.append("max_acceptable_losing_streak is missing")
    elif limits.max_acceptable_losing_streak < 1:
        errors.append("max_acceptable_losing_streak must be >= 1")

    if limits.daily_loss_limit_usd is None:
        errors.append("daily_loss_limit_usd is missing")
    elif limits.daily_loss_limit_usd <= 0:
        errors.append("daily_loss_limit_usd must be > 0")

    if limits.aggregate_program_drawdown_limit_pct is None:
        errors.append("aggregate_program_drawdown_limit_pct is missing")
    elif not (0 < limits.aggregate_program_drawdown_limit_pct < 100):
        errors.append("aggregate_program_drawdown_limit_pct must be in (0, 100)")

    if limits.risk_of_ruin_threshold_pct is None:
        errors.append("risk_of_ruin_threshold_pct is missing")
    elif not (0 < limits.risk_of_ruin_threshold_pct < 100):
        errors.append("risk_of_ruin_threshold_pct must be in (0, 100)")

    return errors


def is_risk_limits_signed(path: str | Path) -> bool:
    try:
        limits = load_risk_limits(path)
    except RiskLimitsError:
        return False
    return not _validation_errors(limits)


def assert_risk_limits_signed(path: str | Path) -> None:
    limits = load_risk_limits(path)
    errors = _validation_errors(limits)
    if errors:
        raise RiskLimitsError(
            f"risk limits at {path} are not signed: " + "; ".join(errors)
        )
