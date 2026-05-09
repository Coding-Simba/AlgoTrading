from algotrading.fillmodel import D2_PLACEHOLDER_TAG
from algotrading.paper.simulator import PaperSimulator, synthetic_bars


def test_synthetic_paper_run_completes() -> None:
    sim = PaperSimulator()
    res = sim.run(synthetic_bars(60))
    assert res.bars_processed == 60
    if res.fills > 0:
        assert res.placeholder_cost_fills == res.fills


def test_mock_broker_uses_placeholder_costs_by_default() -> None:
    from algotrading.paper import MockBroker

    b = MockBroker()
    assert b._cost_tag() == D2_PLACEHOLDER_TAG  # noqa: SLF001
