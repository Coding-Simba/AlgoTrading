"""v0.4 skeleton tests: pure regime classification works; switch policy is gate-blocked."""

import pytest

from algotrading.governance.phase_gates import GateBlocked
from algotrading.strategy_v04 import (
    RegimeInputs,
    RegimeLabel,
    classify_regime,
    select_active_strategy,
)


def test_classify_regime_trend_strong_signal_low_vol() -> None:
    inputs = RegimeInputs(vol_norm=0.0005, trend_strength=0.005, vwap_dev=0.0)
    assert classify_regime(inputs) is RegimeLabel.TREND


def test_classify_regime_meanrev_low_vol_weak_trend() -> None:
    inputs = RegimeInputs(vol_norm=0.0005, trend_strength=0.0005, vwap_dev=0.0)
    assert classify_regime(inputs) is RegimeLabel.MEANREV


def test_classify_regime_meanrev_strong_vwap_dev() -> None:
    inputs = RegimeInputs(vol_norm=0.0010, trend_strength=0.0005, vwap_dev=2.0)
    assert classify_regime(inputs) is RegimeLabel.MEANREV


def test_classify_regime_neutral_otherwise() -> None:
    inputs = RegimeInputs(vol_norm=0.0050, trend_strength=0.0005, vwap_dev=0.5)
    assert classify_regime(inputs) is RegimeLabel.NEUTRAL


def test_classify_regime_neutral_when_strong_trend_high_vol() -> None:
    inputs = RegimeInputs(vol_norm=0.0050, trend_strength=0.005, vwap_dev=0.0)
    assert classify_regime(inputs) is RegimeLabel.NEUTRAL


def test_select_active_strategy_gate_blocked_trend() -> None:
    with pytest.raises(GateBlocked):
        select_active_strategy(RegimeLabel.TREND)


def test_select_active_strategy_gate_blocked_meanrev() -> None:
    with pytest.raises(GateBlocked):
        select_active_strategy(RegimeLabel.MEANREV)


def test_select_active_strategy_gate_blocked_neutral() -> None:
    with pytest.raises(GateBlocked):
        select_active_strategy(RegimeLabel.NEUTRAL)
