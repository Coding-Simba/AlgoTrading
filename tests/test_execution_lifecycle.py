import pytest

from algotrading.orders import (
    ExecutionLifecycle,
    ExecutionState,
    ExecutionStateError,
)


def test_valid_execution_lifecycle_reaches_flat() -> None:
    lc = ExecutionLifecycle()
    assert lc.state is ExecutionState.FLAT
    lc.transition(1, ExecutionState.SIGNAL_PENDING, reason="signal generated")
    lc.transition(2, ExecutionState.ENTRY_SENT, reason="entry submitted")
    lc.transition(3, ExecutionState.ENTRY_FILLED, reason="entry filled")
    lc.transition(4, ExecutionState.BRACKET_PENDING, reason="bracket submitted")
    lc.transition(5, ExecutionState.POSITION_PROTECTED, reason="bracket ack received")
    lc.transition(6, ExecutionState.EXIT_PENDING, reason="target hit")
    lc.transition(7, ExecutionState.FLAT_RECONCILING, reason="exit confirmed by broker")
    lc.transition(8, ExecutionState.FLAT, reason="reconciliation passed")
    assert lc.state is ExecutionState.FLAT
    assert [h[1] for h in lc.history] == [
        ExecutionState.SIGNAL_PENDING,
        ExecutionState.ENTRY_SENT,
        ExecutionState.ENTRY_FILLED,
        ExecutionState.BRACKET_PENDING,
        ExecutionState.POSITION_PROTECTED,
        ExecutionState.EXIT_PENDING,
        ExecutionState.FLAT_RECONCILING,
        ExecutionState.FLAT,
    ]


def test_no_new_entry_outside_flat() -> None:
    lc = ExecutionLifecycle()
    lc.transition(1, ExecutionState.SIGNAL_PENDING, reason="first signal")
    assert not lc.can_emit_entry()
    with pytest.raises(ExecutionStateError, match="new entry rejected"):
        lc.transition(2, ExecutionState.SIGNAL_PENDING, reason="second signal while not flat")

    lc.transition(3, ExecutionState.ENTRY_SENT)
    lc.transition(4, ExecutionState.ENTRY_FILLED)
    lc.transition(5, ExecutionState.BRACKET_PENDING)
    lc.transition(6, ExecutionState.POSITION_PROTECTED)
    assert not lc.can_emit_entry()
    with pytest.raises(ExecutionStateError):
        lc.transition(7, ExecutionState.SIGNAL_PENDING, reason="entry while position open")


def test_bracket_rejection_drives_error_halted() -> None:
    lc = ExecutionLifecycle()
    lc.transition(1, ExecutionState.SIGNAL_PENDING)
    lc.transition(2, ExecutionState.ENTRY_SENT)
    lc.transition(3, ExecutionState.ENTRY_FILLED)
    lc.transition(4, ExecutionState.BRACKET_PENDING)
    lc.transition_to_error(5, reason="bracket rejected by broker — error code 12")
    assert lc.state is ExecutionState.ERROR_HALTED


def test_bracket_ack_timeout_drives_error_halted() -> None:
    lc = ExecutionLifecycle()
    lc.transition(1, ExecutionState.SIGNAL_PENDING)
    lc.transition(2, ExecutionState.ENTRY_SENT)
    lc.transition(3, ExecutionState.ENTRY_FILLED)
    lc.transition(4, ExecutionState.BRACKET_PENDING)
    lc.transition_to_error(5, reason="bracket ack timeout 5s exceeded")
    assert lc.state is ExecutionState.ERROR_HALTED


def test_error_halted_cannot_exit_without_manual_review() -> None:
    lc = ExecutionLifecycle()
    lc.transition_to_error(1, reason="manual operator trip")
    with pytest.raises(ExecutionStateError, match="manual review"):
        lc.transition(2, ExecutionState.FLAT, reason="just flip it")
    lc.transition(3, ExecutionState.FLAT, reason="manual_review passed by RISK-01")
    assert lc.state is ExecutionState.FLAT


def test_error_halted_requires_non_empty_reason() -> None:
    lc = ExecutionLifecycle()
    with pytest.raises(ExecutionStateError):
        lc.transition_to_error(1, reason="   ")


def test_signal_can_be_canceled_back_to_flat() -> None:
    lc = ExecutionLifecycle()
    lc.transition(1, ExecutionState.SIGNAL_PENDING, reason="signal generated")
    lc.transition(2, ExecutionState.FLAT, reason="signal cancelled before send")
    assert lc.state is ExecutionState.FLAT
    assert lc.can_emit_entry()


def test_entry_terminated_without_fill_returns_to_flat() -> None:
    lc = ExecutionLifecycle()
    lc.transition(1, ExecutionState.SIGNAL_PENDING)
    lc.transition(2, ExecutionState.ENTRY_SENT)
    lc.transition(3, ExecutionState.FLAT, reason="entry rejected; no fill; back to flat")
    assert lc.state is ExecutionState.FLAT


def test_invalid_skip_transitions_rejected() -> None:
    lc = ExecutionLifecycle()
    lc.transition(1, ExecutionState.SIGNAL_PENDING)
    with pytest.raises(ExecutionStateError):
        lc.transition(2, ExecutionState.ENTRY_FILLED)
    with pytest.raises(ExecutionStateError):
        lc.transition(3, ExecutionState.POSITION_PROTECTED)


def test_double_error_rejected() -> None:
    lc = ExecutionLifecycle()
    lc.transition_to_error(1, reason="first error")
    with pytest.raises(ExecutionStateError, match="already in ERROR_HALTED"):
        lc.transition_to_error(2, reason="second error")
