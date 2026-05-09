"""Backtest / OOS / holdback gate enforcement.

Wraps ``governance.phase_gates`` with the specific entry-points the
backtest engine, training runner, OOS runner, and holdback runner each
call.
"""

from __future__ import annotations

from pathlib import Path

from ..governance.phase_gates import (
    GateBlocked,
    GateContext,
    assert_approved_backtest_unblocked,
    assert_holdback_unblocked,
    assert_oos_unblocked,
    assert_pre_code_signed,
)


def enforce_synthetic_only(*, label: str = "synthetic") -> None:
    return None


def enforce_approved_backtest(
    repo_root: str | Path,
    *,
    placeholder_costs_present: bool,
) -> None:
    ctx = GateContext.default(repo_root)
    assert_approved_backtest_unblocked(
        ctx,
        placeholder_costs_present=placeholder_costs_present,
    )


def enforce_oos(repo_root: str | Path, *, strategy_version: str = "v0.2") -> None:
    ctx = GateContext.default(repo_root)
    assert_oos_unblocked(ctx, strategy_version=strategy_version)


def enforce_holdback(
    repo_root: str | Path,
    *,
    oos_pass_recorded: bool,
    holdback_trade_count_threshold_met: bool,
) -> None:
    ctx = GateContext.default(repo_root)
    assert_holdback_unblocked(
        ctx,
        oos_pass_recorded=oos_pass_recorded,
        holdback_trade_count_threshold_met=holdback_trade_count_threshold_met,
    )


def enforce_pre_code(repo_root: str | Path) -> None:
    ctx = GateContext.default(repo_root)
    assert_pre_code_signed(ctx)


__all__ = [
    "GateBlocked",
    "enforce_synthetic_only",
    "enforce_approved_backtest",
    "enforce_oos",
    "enforce_holdback",
    "enforce_pre_code",
]
