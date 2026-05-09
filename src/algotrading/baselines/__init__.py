"""Baseline runner skeletons.

Per the spec a strategy must beat a battery of baselines on training data
before it is considered for validation. The baselines defined here are
*runner skeletons*: they accept a bar stream and produce trade signals.
They contain **no** v0.2 strategy logic.

Skeletons:

- ``RandomBaseline``         — uniformly random long/short/flat per bar.
- ``DriftMatchedRandom``     — random direction with bias matching training drift.
- ``ReversedSignalBaseline`` — wraps a real signal source and inverts every signal.
- ``SessionExposureBaseline``— always-long-during-session, flat-overnight.

These are intentionally trivial; their value is as null hypotheses, not as
trading strategies.
"""

from .runners import (
    BaselineRunner,
    RandomBaseline,
    DriftMatchedRandom,
    ReversedSignalBaseline,
    SessionExposureBaseline,
    Signal,
)

__all__ = [
    "BaselineRunner",
    "RandomBaseline",
    "DriftMatchedRandom",
    "ReversedSignalBaseline",
    "SessionExposureBaseline",
    "Signal",
]
