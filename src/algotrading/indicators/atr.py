"""Wilder ATR per Appendix B §B.5.

`alpha = 1 / N`, period 14, on 5-minute bars. True range:

    TR_i = max(high_i - low_i,
               abs(high_i - close_{i-1}),
               abs(low_i  - close_{i-1}))

Seed: simple mean of TR over the first N bars (Wilder convention).
"""

from __future__ import annotations

from collections.abc import Sequence


def wilder_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float | None]:
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    n = len(highs)
    if not (n == len(lows) == len(closes)):
        raise ValueError("highs/lows/closes must be same length")
    out: list[float | None] = [None] * n
    if n < period + 1:
        return out

    trs: list[float] = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    seed = sum(trs[:period]) / period
    out[period] = seed
    prev = seed
    alpha = 1.0 / period
    for i in range(period + 1, n):
        prev = alpha * trs[i - 1] + (1 - alpha) * prev
        out[i] = prev
    return out
