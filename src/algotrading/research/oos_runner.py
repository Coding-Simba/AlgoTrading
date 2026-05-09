"""Out-of-sample (OOS) runner.

Refuses to open the validation partition unless every prerequisite in
``governance.phase_gates.assert_oos_unblocked`` passes.
"""

from __future__ import annotations

from pathlib import Path

from ..backtest.gates import enforce_oos, GateBlocked


class OOSBlocked(GateBlocked):
    pass


class OOSRunner:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    def run(self, *, strategy_version: str = "v0.2") -> None:
        try:
            enforce_oos(self.repo_root, strategy_version=strategy_version)
        except GateBlocked as exc:
            raise OOSBlocked(f"OOS run blocked: {exc}") from exc
        raise OOSBlocked(
            "OOS run blocked: v0.2 does not implement the real-data OOS path; "
            "fixture stub only."
        )
