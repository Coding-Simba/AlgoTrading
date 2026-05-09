"""Training runner.

Synthetic training is permitted at any time. Real-data training
requires pre-code sign-off and a signed partition lock. Approved
backtests still require the broker rate sheet (see
``backtest.gates.enforce_approved_backtest``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..backtest import BacktestEngine, BacktestResult
from ..backtest.gates import enforce_pre_code, GateBlocked
from ..contamination import is_partition_lock_signed
from ..paper.simulator import SyntheticBar


@dataclass
class TrainingResult:
    backtest: BacktestResult
    mode: str  # "synthetic" | "real"
    notes: list[str] = field(default_factory=list)


class TrainingRunner:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    def run_synthetic(self, bars: list[SyntheticBar]) -> TrainingResult:
        engine = BacktestEngine()
        result = engine.run_synthetic(bars)
        return TrainingResult(
            backtest=result,
            mode="synthetic",
            notes=["synthetic training run; not a substitute for real-data training"],
        )

    def run_real(self, bars: list[SyntheticBar]) -> TrainingResult:
        try:
            enforce_pre_code(self.repo_root)
        except GateBlocked as exc:
            raise GateBlocked(f"training (real-data) blocked: {exc}") from exc
        partitions = self.repo_root / "configs" / "data_partitions.yml"
        if not is_partition_lock_signed(partitions):
            raise GateBlocked(
                f"training (real-data) blocked: partition lock at {partitions} not signed"
            )
        engine = BacktestEngine()
        result = engine.run_synthetic(bars)
        return TrainingResult(
            backtest=result,
            mode="real",
            notes=["real-data training stub; engine consumed synthetic shaped fixtures"],
        )
