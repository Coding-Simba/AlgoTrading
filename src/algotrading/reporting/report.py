"""Run reporting.

Renders a :class:`PaperRunResult` (or a :class:`BacktestResult`) into a
plain-text report. Reports carry an explicit `approved` flag and a
prominent `D2_PLACEHOLDER` warning when the underlying fills used
placeholder costs.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..backtest.engine import BacktestResult
from ..fillmodel import D2_PLACEHOLDER_TAG
from ..paper.simulator import PaperRunResult


@dataclass
class RunReport:
    title: str
    approved: bool
    body: str
    placeholder_costs_present: bool

    def render(self) -> str:
        header = f"# {self.title}\n"
        approved_line = f"approved: {self.approved}\n"
        warn = ""
        if self.placeholder_costs_present:
            warn = (
                f"\n!! WARNING: this report carries the {D2_PLACEHOLDER_TAG} tag.\n"
                f"!! The underlying fills used placeholder costs from §D.2.\n"
                f"!! This run is NOT a research-report-quality approved backtest.\n"
                f"!! Replace placeholder costs with the broker rate sheet before approval.\n\n"
            )
        return header + approved_line + warn + self.body


def generate_run_report(result: PaperRunResult | BacktestResult, *, title: str = "v0.2 synthetic run") -> RunReport:
    if isinstance(result, BacktestResult):
        paper = result.paper_result
        approved = result.approved
        placeholder = result.placeholder_cost_tag_present
    else:
        paper = result
        approved = False
        placeholder = paper.placeholder_cost_fills > 0

    body = (
        f"bars_processed:           {paper.bars_processed}\n"
        f"signals_seen:             {paper.signals_seen}\n"
        f"entries_taken:            {paper.entries_taken}\n"
        f"skips_due_to_atr_filter:  {paper.skips_due_to_atr_filter}\n"
        f"skips_due_to_no_trade:    {paper.skips_due_to_no_trade}\n"
        f"fills:                    {paper.fills}\n"
        f"error_halted_count:       {paper.error_halted_count}\n"
        f"placeholder_cost_fills:   {paper.placeholder_cost_fills}\n"
    )
    if paper.notes:
        body += "\nnotes:\n"
        for n in paper.notes:
            body += f"- {n}\n"
    return RunReport(
        title=title,
        approved=approved,
        body=body,
        placeholder_costs_present=placeholder,
    )
