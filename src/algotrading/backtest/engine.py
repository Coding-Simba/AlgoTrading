"""Backtest engine.

Wraps the paper simulator with a result envelope marked
``approved=False`` (synthetic / training mode) by default. Approved
backtests must replace the placeholder costs and call
``gates.enforce_approved_backtest`` before producing a research-grade
report.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..fillmodel import D2_PLACEHOLDER_TAG
from ..paper.simulator import PaperRunResult, PaperSimulator, SyntheticBar


@dataclass
class BacktestResult:
    paper_result: PaperRunResult
    approved: bool = False
    placeholder_cost_tag_present: bool = False
    notes: list[str] = field(default_factory=list)


class BacktestEngine:
    """Synthetic-only by default. Set ``approved=True`` only after
    ``backtest.gates.enforce_approved_backtest`` passes (which itself
    requires `D2_PLACEHOLDER` to NOT be on any fill)."""

    def __init__(self, simulator: PaperSimulator | None = None) -> None:
        self.simulator = simulator or PaperSimulator()

    def run_synthetic(self, bars: list[SyntheticBar]) -> BacktestResult:
        result = self.simulator.run(bars)
        return BacktestResult(
            paper_result=result,
            approved=False,
            placeholder_cost_tag_present=result.placeholder_cost_fills > 0,
            notes=[
                f"D2_PLACEHOLDER tag present on {result.placeholder_cost_fills} fills",
                "approved=False (synthetic). Promote to approved only via "
                "backtest.gates.enforce_approved_backtest()",
            ],
        )

    def stamp_approved(self, result: BacktestResult) -> BacktestResult:
        if result.placeholder_cost_tag_present:
            raise RuntimeError(
                f"approved backtest blocked: {D2_PLACEHOLDER_TAG} present in result"
            )
        result.approved = True
        return result
