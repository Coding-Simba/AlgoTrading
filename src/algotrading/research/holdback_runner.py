"""Final-holdback runner.

Refuses to open the holdback partition unless every prerequisite in
``governance.phase_gates.assert_holdback_unblocked`` passes.
"""

from __future__ import annotations

from pathlib import Path

from ..backtest.gates import enforce_holdback, GateBlocked


class HoldbackBlocked(GateBlocked):
    pass


class HoldbackRunner:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    def run(
        self,
        *,
        oos_pass_recorded: bool = False,
        holdback_trade_count_threshold_met: bool = False,
    ) -> None:
        try:
            enforce_holdback(
                self.repo_root,
                oos_pass_recorded=oos_pass_recorded,
                holdback_trade_count_threshold_met=holdback_trade_count_threshold_met,
            )
        except GateBlocked as exc:
            raise HoldbackBlocked(f"holdback run blocked: {exc}") from exc
        raise HoldbackBlocked(
            "holdback run blocked: v0.2 does not implement the real-data "
            "holdback path; fixture stub only."
        )
