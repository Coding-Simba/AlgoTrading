"""5m / 60m bar builder with strict boundary semantics (per §B.5).

Boundary rules:

- A bar is identified by ``open_ns``, the inclusive start of its window.
- A tick at exactly ``open_ns + interval_ns`` belongs to the **next** bar.
- A tick at exactly ``open_ns`` belongs to **this** bar (not the previous one).
- A bar with zero ticks emits no Bar record. The next non-empty bar starts
  at the floor of the new tick's timestamp; the gap is recoverable from
  ``open_ns`` deltas. Filling gaps is a downstream concern.

This is the spec-exact behaviour required for B.5 boundary tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from ..ingestion.types import Tick


class BarBuilderError(RuntimeError):
    pass


_NS_PER_S = 1_000_000_000
FIVE_MIN = 5 * 60 * _NS_PER_S
SIXTY_MIN = 60 * 60 * _NS_PER_S


@dataclass(frozen=True, slots=True)
class Bar:
    open_ns: int
    close_ns: int
    open: int
    high: int
    low: int
    close: int
    volume: int
    tick_count: int
    interval_ns: int


class BarBuilder:
    def __init__(self, interval_ns: int, *, anchor_ns: int = 0) -> None:
        if interval_ns <= 0:
            raise BarBuilderError(f"interval_ns must be positive, got {interval_ns}")
        self.interval_ns = interval_ns
        self.anchor_ns = anchor_ns
        self._open_ns: int | None = None
        self._open: int | None = None
        self._high: int | None = None
        self._low: int | None = None
        self._close: int | None = None
        self._volume: int = 0
        self._count: int = 0

    def _floor(self, ts_ns: int) -> int:
        delta = ts_ns - self.anchor_ns
        return self.anchor_ns + (delta // self.interval_ns) * self.interval_ns

    def push(self, tick: Tick) -> Bar | None:
        completed: Bar | None = None
        bar_open = self._floor(tick.ts_ns)

        if self._open_ns is None:
            self._begin(bar_open, tick)
            return None

        if bar_open == self._open_ns:
            self._extend(tick)
            return None

        if bar_open < self._open_ns:
            raise BarBuilderError(
                f"non-monotonic tick: ts_ns={tick.ts_ns} floors to {bar_open} "
                f"but current bar opens at {self._open_ns}"
            )

        completed = self._snapshot()
        self._begin(bar_open, tick)
        return completed

    def flush(self) -> Bar | None:
        if self._open_ns is None:
            return None
        b = self._snapshot()
        self._open_ns = None
        self._open = self._high = self._low = self._close = None
        self._volume = 0
        self._count = 0
        return b

    def _begin(self, bar_open: int, tick: Tick) -> None:
        self._open_ns = bar_open
        self._open = self._high = self._low = self._close = tick.price
        self._volume = tick.size
        self._count = 1

    def _extend(self, tick: Tick) -> None:
        assert self._open is not None
        assert self._high is not None and self._low is not None
        if tick.price > self._high:
            self._high = tick.price
        if tick.price < self._low:
            self._low = tick.price
        self._close = tick.price
        self._volume += tick.size
        self._count += 1

    def _snapshot(self) -> Bar:
        assert self._open_ns is not None
        assert self._open is not None
        assert self._high is not None and self._low is not None
        assert self._close is not None
        return Bar(
            open_ns=self._open_ns,
            close_ns=self._open_ns + self.interval_ns,
            open=self._open,
            high=self._high,
            low=self._low,
            close=self._close,
            volume=self._volume,
            tick_count=self._count,
            interval_ns=self.interval_ns,
        )


def build_bars(ticks: Iterable[Tick], interval_ns: int, *, anchor_ns: int = 0) -> Iterator[Bar]:
    builder = BarBuilder(interval_ns, anchor_ns=anchor_ns)
    for t in ticks:
        bar = builder.push(t)
        if bar is not None:
            yield bar
    final = builder.flush()
    if final is not None:
        yield final
