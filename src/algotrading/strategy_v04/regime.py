"""Regime classifier per Appendix B v0.4 §B_v0.4.3.

Pure function: same inputs → same label. Not gate-blocked (it produces a
label, not a trade decision).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RegimeLabel(str, Enum):
    TREND = "trend"
    MEANREV = "meanrev"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class RegimeInputs:
    vol_norm: float
    trend_strength: float  # signed
    vwap_dev: float        # signed (in ATR units)


_TREND_STRENGTH_STRONG = 0.0030
_TREND_STRENGTH_WEAK = 0.0010
_VOL_NORM_LOW = 0.0008
_VWAP_DEV_STRONG = 1.5


def classify_regime(inputs: RegimeInputs) -> RegimeLabel:
    abs_trend = abs(inputs.trend_strength)
    if abs_trend >= _TREND_STRENGTH_STRONG and inputs.vol_norm <= _VOL_NORM_LOW:
        return RegimeLabel.TREND
    if abs_trend <= _TREND_STRENGTH_WEAK and inputs.vol_norm <= _VOL_NORM_LOW:
        return RegimeLabel.MEANREV
    if abs_trend <= _TREND_STRENGTH_WEAK and abs(inputs.vwap_dev) >= _VWAP_DEV_STRONG:
        return RegimeLabel.MEANREV
    return RegimeLabel.NEUTRAL
