"""Session VWAP per Appendix B §B.5.

`vwap = sum(price * volume) / sum(volume)` over the session, reset at the
session-open boundary. The "session" boundary is supplied by the caller
as a list of session-start indices (or by the session calendar in real
ingestion).
"""

from __future__ import annotations

from collections.abc import Sequence


def session_vwap(
    prices: Sequence[float],
    volumes: Sequence[float],
    session_start_indices: Sequence[int],
) -> list[float | None]:
    """Return a per-tick / per-bar VWAP series, reset at each
    session_start index.

    ``session_start_indices`` must be sorted ascending, with 0 typically
    as the first element. Indices outside ``[0, len(prices))`` are
    rejected.
    """
    n = len(prices)
    if n != len(volumes):
        raise ValueError("prices and volumes must be same length")
    starts = sorted(set(int(s) for s in session_start_indices))
    if starts and (starts[0] < 0 or starts[-1] >= n):
        raise ValueError("session_start_indices out of range")
    out: list[float | None] = [None] * n
    if not starts:
        return out
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else n
        cum_pv = 0.0
        cum_v = 0.0
        for j in range(start, end):
            cum_pv += prices[j] * volumes[j]
            cum_v += volumes[j]
            out[j] = cum_pv / cum_v if cum_v > 0 else None
    return out
