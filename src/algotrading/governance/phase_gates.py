"""Phase-gate enforcement helpers used by the runners.

Each function refuses the named phase unless the prerequisites it lists
are satisfied. Prerequisite values come from
``configs/signoff_matrix.yml``, ``configs/risk_limits.yml``, and
``configs/data_partitions.yml`` plus a small set of runtime checks (e.g.,
"this fill stream has no D2_PLACEHOLDER tag").

Functions raise :class:`GateBlocked` with a structured reason on refusal.
There is no override flag — bypassing a gate requires editing the
governance code under Risk Reviewer review.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .signoff import SignoffError, SignoffMatrix, load_matrix, require_signed
from .risk_limits import RiskLimitsError, is_risk_limits_signed
from ..contamination import is_partition_lock_signed


class GateBlocked(RuntimeError):
    """Raised when a phase-gate prerequisite is not satisfied."""


@dataclass(frozen=True)
class GateContext:
    signoff_path: Path
    risk_limits_path: Path
    partitions_path: Path
    contamination_log_path: Path

    @classmethod
    def default(cls, repo_root: str | Path) -> "GateContext":
        root = Path(repo_root)
        return cls(
            signoff_path=root / "configs" / "signoff_matrix.yml",
            risk_limits_path=root / "configs" / "risk_limits.yml",
            partitions_path=root / "configs" / "data_partitions.yml",
            contamination_log_path=root / "docs" / "research_contamination_log" / "research_contamination_log.csv",
        )


def _safe_load_matrix(ctx: GateContext) -> SignoffMatrix:
    try:
        return load_matrix(ctx.signoff_path)
    except SignoffError as exc:
        raise GateBlocked(f"sign-off matrix unreadable: {exc}") from exc


def assert_pre_code_signed(ctx: GateContext) -> None:
    matrix = _safe_load_matrix(ctx)
    try:
        require_signed(matrix, gate="v0.2_code")
    except SignoffError as exc:
        raise GateBlocked(f"pre-code sign-off incomplete: {exc}") from exc


def assert_v03_code_unblocked(ctx: GateContext) -> None:
    matrix = _safe_load_matrix(ctx)
    try:
        require_signed(matrix, gate="v0.3_code")
    except SignoffError as exc:
        raise GateBlocked(f"v0.3 code execution blocked: {exc}") from exc


def assert_v04_code_unblocked(ctx: GateContext) -> None:
    matrix = _safe_load_matrix(ctx)
    try:
        require_signed(matrix, gate="v0.4_code")
    except SignoffError as exc:
        raise GateBlocked(f"v0.4 code execution blocked: {exc}") from exc


def assert_training_unblocked(ctx: GateContext) -> None:
    assert_pre_code_signed(ctx)
    if not is_partition_lock_signed(ctx.partitions_path):
        raise GateBlocked(
            "training against real partitions blocked: partition lock at "
            f"{ctx.partitions_path} is not signed"
        )


def assert_approved_backtest_unblocked(
    ctx: GateContext,
    *,
    placeholder_costs_present: bool,
    risk_limits_signed_required: bool = True,
) -> None:
    assert_pre_code_signed(ctx)
    matrix = _safe_load_matrix(ctx)
    rate_sheet = matrix.find("broker_rate_sheet")
    if rate_sheet is None or not rate_sheet.signed:
        raise GateBlocked(
            "approved backtest blocked: broker_rate_sheet row in "
            "configs/signoff_matrix.yml is not signed (errata §5)"
        )
    if placeholder_costs_present:
        raise GateBlocked(
            "approved backtest blocked: fill stream still carries "
            "D2_PLACEHOLDER costs (errata §5)"
        )
    if risk_limits_signed_required and not is_risk_limits_signed(ctx.risk_limits_path):
        raise GateBlocked(
            f"approved backtest blocked: risk limits at {ctx.risk_limits_path} "
            "are not signed"
        )


def assert_oos_unblocked(ctx: GateContext, *, strategy_version: str) -> None:
    matrix = _safe_load_matrix(ctx)
    vf = matrix.find("validation_freeze")
    if vf is None or not vf.signed:
        raise GateBlocked(
            "OOS blocked: validation_freeze row in configs/signoff_matrix.yml "
            "is not signed"
        )
    if not is_partition_lock_signed(ctx.partitions_path):
        raise GateBlocked(
            f"OOS blocked: partition lock at {ctx.partitions_path} is not signed"
        )
    from ..contamination import enforce_no_validation_before_freeze, PartitionLockMissing
    try:
        enforce_no_validation_before_freeze(
            strategy_version=strategy_version,
            partitions_path=ctx.partitions_path,
            contamination_log_path=ctx.contamination_log_path,
        )
    except PartitionLockMissing as exc:
        raise GateBlocked(f"OOS blocked: {exc}") from exc


def assert_holdback_unblocked(
    ctx: GateContext,
    *,
    oos_pass_recorded: bool,
    holdback_trade_count_threshold_met: bool,
) -> None:
    if not is_partition_lock_signed(ctx.partitions_path):
        raise GateBlocked(
            f"holdback blocked: partition lock at {ctx.partitions_path} is not signed"
        )
    if not oos_pass_recorded:
        raise GateBlocked("holdback blocked: OOS pass for the family is not recorded")
    if not holdback_trade_count_threshold_met:
        raise GateBlocked(
            "holdback blocked: holdback-partition trade-count floor not met "
            "(see docs/data/partition_plan.md §7: 300 family / 150 per side)"
        )


def assert_paper_unblocked(ctx: GateContext) -> None:
    matrix = _safe_load_matrix(ctx)
    f_row = matrix.find("F")
    if f_row is None or not f_row.signed:
        raise GateBlocked(
            "paper trading blocked: Appendix F (broker integration & OCO "
            "finalization) is not signed for the chosen broker"
        )


def assert_live_unblocked(
    ctx: GateContext,
    *,
    broker_oco_confirmed: bool,
    broker_costs_inserted: bool,
    appendix_f_runbook_complete: bool,
    account_controls_configured: bool,
    max_order_size_one_mes: bool,
    explicit_live_enable_flag: bool,
) -> None:
    matrix = _safe_load_matrix(ctx)
    paper_row = matrix.find("paper")
    if paper_row is None or not paper_row.signed:
        raise GateBlocked("live blocked: paper-gate row is not signed")
    if not broker_oco_confirmed:
        raise GateBlocked("live blocked: broker OCO confirmation missing")
    if not broker_costs_inserted:
        raise GateBlocked("live blocked: broker costs not yet inserted (errata §5)")
    if not appendix_f_runbook_complete:
        raise GateBlocked("live blocked: Appendix F broker-specific runbook incomplete")
    if not account_controls_configured:
        raise GateBlocked("live blocked: account controls not configured")
    if not max_order_size_one_mes:
        raise GateBlocked("live blocked: max order size must be 1 MES at small-size live")
    if not explicit_live_enable_flag:
        raise GateBlocked(
            "live blocked: explicit live-enable flag missing (live adapter refuses by default)"
        )
    small_size_row = matrix.find("small_size_live")
    if small_size_row is None:
        raise GateBlocked("live blocked: small_size_live row absent from signoff matrix")


def assert_scaleup_unblocked(ctx: GateContext) -> None:
    matrix = _safe_load_matrix(ctx)
    g_row = matrix.find("G")
    if g_row is None or not g_row.signed:
        raise GateBlocked("scale-up blocked: Appendix G is not signed")
    small_size_row = matrix.find("small_size_live")
    if small_size_row is None or not small_size_row.signed:
        raise GateBlocked("scale-up blocked: small-size live row is not signed")


def gate_summary(ctx: GateContext) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}

    for name, fn in (
        ("v0.2_code", lambda: assert_pre_code_signed(ctx)),
        ("v0.3_code", lambda: assert_v03_code_unblocked(ctx)),
        ("v0.4_code", lambda: assert_v04_code_unblocked(ctx)),
        (
            "approved_backtest",
            lambda: assert_approved_backtest_unblocked(
                ctx,
                placeholder_costs_present=True,
                risk_limits_signed_required=True,
            ),
        ),
        (
            "oos",
            lambda: assert_oos_unblocked(ctx, strategy_version="v0.2"),
        ),
        (
            "holdback",
            lambda: assert_holdback_unblocked(
                ctx,
                oos_pass_recorded=False,
                holdback_trade_count_threshold_met=False,
            ),
        ),
        ("paper", lambda: assert_paper_unblocked(ctx)),
        (
            "live",
            lambda: assert_live_unblocked(
                ctx,
                broker_oco_confirmed=False,
                broker_costs_inserted=False,
                appendix_f_runbook_complete=False,
                account_controls_configured=False,
                max_order_size_one_mes=True,
                explicit_live_enable_flag=False,
            ),
        ),
        ("scaleup", lambda: assert_scaleup_unblocked(ctx)),
    ):
        try:
            fn()
        except (GateBlocked, RiskLimitsError) as exc:
            summary[name] = {"status": "BLOCKED", "reason": str(exc)}
        else:
            summary[name] = {"status": "ALLOWED", "reason": None}
    return summary
