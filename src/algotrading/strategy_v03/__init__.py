"""Strategy v0.3 — intraday mean-reversion to session VWAP.

Skeleton registered via CR-001. Entry-rule and stop/target functions are
gate-blocked: they require the ``B_v0.3`` row in
``configs/signoff_matrix.yml`` to be signed before they will run.

Pure classification helpers (``classify_extension_long`` /
``classify_extension_short``) are exposed for unit tests and audit and are
not gate-blocked.

See ``docs/appendices/B_strategy_spec_v0_3.md``.
"""

from .rules import (
    Bar5m,
    EntrySide,
    EntrySignal,
    StopTargetPlan,
    classify_extension_long,
    classify_extension_short,
    long_signal_v03,
    plan_long_v03,
    plan_short_v03,
    short_signal_v03,
)

__all__ = [
    "Bar5m",
    "EntrySide",
    "EntrySignal",
    "StopTargetPlan",
    "classify_extension_long",
    "classify_extension_short",
    "long_signal_v03",
    "plan_long_v03",
    "plan_short_v03",
    "short_signal_v03",
]
