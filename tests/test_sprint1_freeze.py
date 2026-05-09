"""Sprint 1 freeze guard — superseded.

Sprint 1 forbade v0.2 strategy logic. With the user's overnight build
authorization, v0.2 implementation is now permitted under
``src/algotrading/strategy_v02/`` and the gate-based phase enforcement
in ``src/algotrading/governance/phase_gates.py``.

This file is kept as a documentation marker so the historical guard's
role is visible in `git log`. The active enforcement is now:

- ``tests/test_phase1_gate.py`` — refuses signed-fixture flips without
  the corresponding governance state.
- ``tests/test_app_gates.py`` — exercises every runtime gate against the
  real (unsigned) configs to confirm BLOCKED state today.

If you are looking for the original symbol-pattern guard, see git
history of this file pre-build.
"""


def test_sprint1_freeze_superseded_by_phase_gates() -> None:
    """Marker test: confirms the runtime phase-gate path exists.

    The Sprint 1 freeze was a coarse symbol-name check. It has been
    replaced by the runtime gate system; the marker below imports the
    successor surface to ensure it doesn't quietly disappear.
    """
    from algotrading.governance.phase_gates import (
        GateBlocked,
        assert_pre_code_signed,
        assert_approved_backtest_unblocked,
        assert_oos_unblocked,
        assert_holdback_unblocked,
        assert_paper_unblocked,
        assert_live_unblocked,
        assert_scaleup_unblocked,
    )

    assert all(
        callable(fn)
        for fn in (
            assert_pre_code_signed,
            assert_approved_backtest_unblocked,
            assert_oos_unblocked,
            assert_holdback_unblocked,
            assert_paper_unblocked,
            assert_live_unblocked,
            assert_scaleup_unblocked,
        )
    )
    assert issubclass(GateBlocked, RuntimeError)
