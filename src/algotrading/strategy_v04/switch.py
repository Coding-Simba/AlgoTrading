"""Strategy-switch policy per Appendix B v0.4 §B_v0.4.4.

Gate-blocked: refuses unless ``B_v0.4`` row in
``configs/signoff_matrix.yml`` is signed.
"""

from __future__ import annotations

from pathlib import Path

from ..governance.phase_gates import GateContext, assert_v04_code_unblocked
from .regime import RegimeLabel


_REPO_ROOT = Path(__file__).resolve().parents[3]


def select_active_strategy(label: RegimeLabel) -> str | None:
    """Return the active underlying strategy version for the regime
    label, or None if no strategy is active under this regime.
    """
    assert_v04_code_unblocked(GateContext.default(_REPO_ROOT))
    if label is RegimeLabel.TREND:
        return "v0.2"
    if label is RegimeLabel.MEANREV:
        return "v0.3"
    return None
