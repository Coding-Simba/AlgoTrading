"""Standard EMA per Appendix B §B.5.

`alpha = 2 / (N + 1)`, seeded with the simple average of the first N
closed bars.
"""

from __future__ import annotations

from collections.abc import Sequence


def ema_seed(values: Sequence[float], period: int) -> float:
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if len(values) < period:
        raise ValueError(f"need at least {period} values to seed EMA, got {len(values)}")
    return sum(values[:period]) / period


def ema(values: Sequence[float], period: int) -> list[float | None]:
    """Return a list aligned to ``values``: positions < period-1 are None,
    position period-1 is the seed (simple average of first N), and from
    position period onward use the standard EMA recurrence.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    out: list[float | None] = [None] * len(values)
    if len(values) < period:
        return out
    alpha = 2.0 / (period + 1)
    seed = ema_seed(values, period)
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out[i] = prev
    return out
