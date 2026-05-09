"""Baseline signal runners.

A ``Signal`` is one of -1 (short), 0 (flat), +1 (long). Runners take a stream
of bars and emit one signal per bar.

These runners are pure and deterministic given a seed. They do not consult
the validation partition. Running them on training data is logged at the
strategy-version level (per the contamination README), not per execution.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Callable, Protocol

from ..bars import Bar
from ..calendar import SessionCalendar


Signal = int


class BaselineRunner(Protocol):
    name: str

    def __call__(self, bars: Iterable[Bar]) -> Iterator[Signal]:
        ...


@dataclass
class RandomBaseline:
    seed: int = 0
    p_long: float = 1 / 3
    p_short: float = 1 / 3
    name: str = "random"

    def __post_init__(self) -> None:
        if self.p_long < 0 or self.p_short < 0 or self.p_long + self.p_short > 1:
            raise ValueError("invalid probabilities for RandomBaseline")

    def __call__(self, bars: Iterable[Bar]) -> Iterator[Signal]:
        rng = random.Random(self.seed)
        for _ in bars:
            r = rng.random()
            if r < self.p_long:
                yield 1
            elif r < self.p_long + self.p_short:
                yield -1
            else:
                yield 0


@dataclass
class DriftMatchedRandom:
    drift_per_bar: float
    seed: int = 0
    name: str = "drift_matched_random"

    def __call__(self, bars: Iterable[Bar]) -> Iterator[Signal]:
        rng = random.Random(self.seed)
        bias = 0.5 + max(min(self.drift_per_bar * 50.0, 0.4), -0.4)
        for _ in bars:
            yield 1 if rng.random() < bias else -1


@dataclass
class ReversedSignalBaseline:
    inner: Callable[[Iterable[Bar]], Iterable[Signal]]
    name: str = "reversed_signal"

    def __call__(self, bars: Iterable[Bar]) -> Iterator[Signal]:
        for s in self.inner(bars):
            yield -s


@dataclass
class SessionExposureBaseline:
    calendar: SessionCalendar
    name: str = "session_exposure"

    def __call__(self, bars: Iterable[Bar]) -> Iterator[Signal]:
        for bar in bars:
            yield 1 if self.calendar.is_open(bar.open_ns) else 0
