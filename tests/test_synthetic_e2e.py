"""End-to-end synthetic run + report rendering smoke."""

from algotrading.backtest import BacktestEngine
from algotrading.fillmodel import D2_PLACEHOLDER_TAG
from algotrading.paper.simulator import synthetic_bars
from algotrading.reporting import generate_run_report


def test_synthetic_e2e_produces_report_marked_unapproved() -> None:
    engine = BacktestEngine()
    result = engine.run_synthetic(synthetic_bars(60))
    assert result.approved is False
    rep = generate_run_report(result, title="E2E test")
    rendered = rep.render()
    assert "approved: False" in rendered
    if result.placeholder_cost_tag_present:
        assert D2_PLACEHOLDER_TAG in rendered


def test_stamp_approved_refuses_when_placeholder_tag_present() -> None:
    import pytest

    engine = BacktestEngine()
    result = engine.run_synthetic(synthetic_bars(20))
    if result.placeholder_cost_tag_present:
        with pytest.raises(RuntimeError, match=D2_PLACEHOLDER_TAG):
            engine.stamp_approved(result)
