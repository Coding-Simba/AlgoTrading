"""v0.3 skeleton tests: pure helpers work; gate-blocked entry/plan funcs refuse."""

import pytest

from algotrading.governance.phase_gates import GateBlocked
from algotrading.strategy_v03 import (
    Bar5m,
    classify_extension_long,
    classify_extension_short,
    long_signal_v03,
    plan_long_v03,
    plan_short_v03,
    short_signal_v03,
)


def test_classify_extension_long_at_threshold() -> None:
    assert classify_extension_long(close=4490.0, session_vwap=4500.0, atr14=4.0) is True
    assert classify_extension_long(close=4495.0, session_vwap=4500.0, atr14=4.0) is False


def test_classify_extension_short_at_threshold() -> None:
    assert classify_extension_short(close=4510.0, session_vwap=4500.0, atr14=4.0) is True
    assert classify_extension_short(close=4505.0, session_vwap=4500.0, atr14=4.0) is False


def test_classify_extension_custom_multiplier() -> None:
    assert classify_extension_long(
        close=4498.0, session_vwap=4500.0, atr14=4.0, extension_multiplier=0.5
    ) is True


def test_long_signal_v03_gate_blocked() -> None:
    with pytest.raises(GateBlocked):
        long_signal_v03(
            bars5m=[
                Bar5m(high=4500, low=4495, close=4496),
                Bar5m(high=4498, low=4493, close=4494),
                Bar5m(high=4497, low=4494, close=4496),
            ],
            ema50_60m=4500.0,
            ema200_60m=4500.0,
            close_60m=4500.0,
            session_vwap_5m=[4500.0, 4500.0, 4500.0],
            atr14_5m=[4.0, 4.0, 4.0],
        )


def test_short_signal_v03_gate_blocked() -> None:
    with pytest.raises(GateBlocked):
        short_signal_v03(
            bars5m=[
                Bar5m(high=4505, low=4500, close=4504),
                Bar5m(high=4507, low=4502, close=4506),
                Bar5m(high=4506, low=4503, close=4504),
            ],
            ema50_60m=4500.0,
            ema200_60m=4500.0,
            close_60m=4500.0,
            session_vwap_5m=[4500.0, 4500.0, 4500.0],
            atr14_5m=[4.0, 4.0, 4.0],
        )


def test_plan_long_v03_gate_blocked() -> None:
    with pytest.raises(GateBlocked):
        plan_long_v03(
            pullback_low=4495,
            current_ask=4500,
            modeled_slippage_ticks=1,
            atr14=4.0,
            session_vwap=4505.0,
        )


def test_plan_short_v03_gate_blocked() -> None:
    with pytest.raises(GateBlocked):
        plan_short_v03(
            pullback_high=4510,
            current_bid=4505,
            modeled_slippage_ticks=1,
            atr14=4.0,
            session_vwap=4500.0,
        )
