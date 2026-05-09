import pytest

from algotrading.orders import (
    ATOMIC_FLATTEN_SEQUENCE,
    DEFAULT_FLATTEN_SEQUENCE,
    FlattenSequenceError,
    FlattenStep,
    protected_flatten_plan,
    validate_flatten_plan,
)


def test_default_plan_is_protected_flatten() -> None:
    plan = protected_flatten_plan()
    assert plan == DEFAULT_FLATTEN_SEQUENCE
    assert plan == (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.KEEP_STOP_ACTIVE,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
        FlattenStep.CANCEL_REMAINING_OCO,
    )


def test_default_plan_keeps_stop_active_until_after_flatten() -> None:
    plan = protected_flatten_plan()
    keep_idx = plan.index(FlattenStep.KEEP_STOP_ACTIVE)
    flatten_idx = plan.index(FlattenStep.SUBMIT_MARKET_FLATTEN)
    confirm_idx = plan.index(FlattenStep.CONFIRM_BROKER_FLAT)
    cancel_idx = plan.index(FlattenStep.CANCEL_REMAINING_OCO)
    assert keep_idx < flatten_idx < confirm_idx < cancel_idx


def test_atomic_flatten_requires_documented_broker_path() -> None:
    with pytest.raises(FlattenSequenceError, match="documented"):
        protected_flatten_plan(atomic_flatten=True, broker_atomic_flatten_documented=False)


def test_atomic_flatten_with_documentation_returns_atomic_sequence() -> None:
    plan = protected_flatten_plan(atomic_flatten=True, broker_atomic_flatten_documented=True)
    assert plan == ATOMIC_FLATTEN_SEQUENCE
    assert FlattenStep.ATOMIC_FLATTEN in plan
    assert FlattenStep.CANCEL_REMAINING_OCO not in plan
    assert FlattenStep.SUBMIT_MARKET_FLATTEN not in plan


def test_validate_default_plan_passes() -> None:
    validate_flatten_plan(protected_flatten_plan())


def test_validate_atomic_plan_passes_with_atomic_flag() -> None:
    plan = protected_flatten_plan(atomic_flatten=True, broker_atomic_flatten_documented=True)
    validate_flatten_plan(plan, atomic_flatten=True)


def test_validate_rejects_cancel_before_flatten() -> None:
    bad_plan = (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.CANCEL_REMAINING_OCO,
        FlattenStep.KEEP_STOP_ACTIVE,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
    )
    with pytest.raises(FlattenSequenceError, match="CANCEL_REMAINING_OCO must come AFTER"):
        validate_flatten_plan(bad_plan)


def test_validate_rejects_default_plan_missing_keep_stop_active() -> None:
    bad_plan = (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
        FlattenStep.CANCEL_REMAINING_OCO,
    )
    with pytest.raises(FlattenSequenceError, match="KEEP_STOP_ACTIVE"):
        validate_flatten_plan(bad_plan)


def test_validate_rejects_keep_after_flatten() -> None:
    bad_plan = (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.KEEP_STOP_ACTIVE,
        FlattenStep.CONFIRM_BROKER_FLAT,
        FlattenStep.CANCEL_REMAINING_OCO,
    )
    with pytest.raises(FlattenSequenceError, match="KEEP_STOP_ACTIVE must precede"):
        validate_flatten_plan(bad_plan)


def test_validate_rejects_atomic_plan_with_oco_cancel() -> None:
    bad_plan = (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.ATOMIC_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
        FlattenStep.CANCEL_REMAINING_OCO,
    )
    with pytest.raises(FlattenSequenceError, match="atomic_flatten plan must not include CANCEL_REMAINING_OCO"):
        validate_flatten_plan(bad_plan, atomic_flatten=True)


def test_validate_rejects_atomic_plan_missing_atomic_step() -> None:
    bad_plan = (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
    )
    with pytest.raises(FlattenSequenceError, match="ATOMIC_FLATTEN"):
        validate_flatten_plan(bad_plan, atomic_flatten=True)


def test_validate_rejects_empty_plan() -> None:
    with pytest.raises(FlattenSequenceError, match="must not be empty"):
        validate_flatten_plan(())


def test_validate_rejects_halt_not_first() -> None:
    bad_plan = (
        FlattenStep.KEEP_STOP_ACTIVE,
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
        FlattenStep.CANCEL_REMAINING_OCO,
    )
    with pytest.raises(FlattenSequenceError, match="HALT_NEW_ENTRIES must be the first"):
        validate_flatten_plan(bad_plan)


def test_cancel_first_rejected_unless_atomic_flatten_flag() -> None:
    """Belt-and-braces: a cancel-before-flatten plan is rejected by the
    default-mode validator AND the atomic-mode validator (because atomic
    plans must use ATOMIC_FLATTEN, not OCO cancel)."""
    cancel_first_plan = (
        FlattenStep.HALT_NEW_ENTRIES,
        FlattenStep.CANCEL_REMAINING_OCO,
        FlattenStep.SUBMIT_MARKET_FLATTEN,
        FlattenStep.CONFIRM_BROKER_FLAT,
    )
    with pytest.raises(FlattenSequenceError):
        validate_flatten_plan(cancel_first_plan, atomic_flatten=False)
    with pytest.raises(FlattenSequenceError):
        validate_flatten_plan(cancel_first_plan, atomic_flatten=True)
