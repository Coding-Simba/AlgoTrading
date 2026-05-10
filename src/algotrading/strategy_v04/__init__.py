"""Strategy v0.4 — rule-based regime classifier and switch policy.

Skeleton registered via CR-001. The switch-policy function
(``select_active_strategy``) is gate-blocked: it requires the ``B_v0.4``
row in ``configs/signoff_matrix.yml`` to be signed before it will run.

The pure ``classify_regime`` function is not gate-blocked: it is
used for unit tests and offline audit only and produces a label, not a
trade decision.

See ``docs/appendices/B_strategy_spec_v0_4.md``.
"""

from .regime import RegimeInputs, RegimeLabel, classify_regime
from .switch import select_active_strategy

__all__ = [
    "RegimeInputs",
    "RegimeLabel",
    "classify_regime",
    "select_active_strategy",
]
