"""Skeleton ingestion pipeline.

Wires raw tick / BBO sources to downstream consumers (bar builder, fill
model, monitoring). Real connections to vendor APIs will be added in a
later sprint; this skeleton provides the seam.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from .types import BBOQuote, Tick


@dataclass
class IngestionPipeline:
    tick_sources: list[Iterable[Tick]] = field(default_factory=list)
    bbo_sources: list[Iterable[BBOQuote]] = field(default_factory=list)

    def add_tick_source(self, source: Iterable[Tick]) -> None:
        self.tick_sources.append(source)

    def add_bbo_source(self, source: Iterable[BBOQuote]) -> None:
        self.bbo_sources.append(source)

    def merged_ticks(self) -> Iterator[Tick]:
        return _ts_merge(self.tick_sources, key=lambda t: t.ts_ns)

    def merged_bbo(self) -> Iterator[BBOQuote]:
        return _ts_merge(self.bbo_sources, key=lambda q: q.ts_ns)


def _ts_merge(iterables, key):
    iterators = [iter(it) for it in iterables]
    heads: list = []
    for i, it in enumerate(iterators):
        try:
            heads.append([key(next_v := next(it)), i, next_v])
        except StopIteration:
            heads.append(None)
    while any(h is not None for h in heads):
        live = [h for h in heads if h is not None]
        live.sort(key=lambda h: (h[0], h[1]))
        chosen = live[0]
        idx = chosen[1]
        yield chosen[2]
        try:
            nxt = next(iterators[idx])
            heads[idx] = [key(nxt), idx, nxt]
        except StopIteration:
            heads[idx] = None
