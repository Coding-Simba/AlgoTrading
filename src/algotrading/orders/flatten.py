"""Protected flatten sequencing (per Appendix H §1.e).

The default flatten sequence keeps the protective stop ACTIVE until the
broker confirms the position is flat. The remaining OCO leg is cancelled
*after* the broker confirms flat, never before. Cancel-first is permitted
only when the broker offers a documented broker-native atomic flatten
(``atomic_flatten=True`` AND ``broker_atomic_flatten_documented=True``).

Default sequence:

    1. HALT_NEW_ENTRIES
    2. KEEP_STOP_ACTIVE              (do not cancel the protective stop)
    3. SUBMIT_MARKET_FLATTEN
    4. CONFIRM_BROKER_FLAT
    5. CANCEL_REMAINING_OCO          (only after step 4)

If position flips or broker / internal mismatch is observed at any
point: ERROR_HALTED.

Atomic sequence (only when documented broker-native atomic flatten
exists):

    1. HALT_NEW_ENTRIES
    2. ATOMIC_FLATTEN                 (broker-native single call)
    3. CONFIRM_BROKER_FLAT
"""

from __future__ import annotations

from enum import Enum


class FlattenSequenceError(RuntimeError):
    pass


class FlattenStep(str, Enum):
    HALT_NEW_ENTRIES = "halt_new_entries"
    KEEP_STOP_ACTIVE = "keep_stop_active"
    SUBMIT_MARKET_FLATTEN = "submit_market_flatten"
    CONFIRM_BROKER_FLAT = "confirm_broker_flat"
    CANCEL_REMAINING_OCO = "cancel_remaining_oco"
    ATOMIC_FLATTEN = "atomic_flatten"


DEFAULT_FLATTEN_SEQUENCE: tuple[FlattenStep, ...] = (
    FlattenStep.HALT_NEW_ENTRIES,
    FlattenStep.KEEP_STOP_ACTIVE,
    FlattenStep.SUBMIT_MARKET_FLATTEN,
    FlattenStep.CONFIRM_BROKER_FLAT,
    FlattenStep.CANCEL_REMAINING_OCO,
)


ATOMIC_FLATTEN_SEQUENCE: tuple[FlattenStep, ...] = (
    FlattenStep.HALT_NEW_ENTRIES,
    FlattenStep.ATOMIC_FLATTEN,
    FlattenStep.CONFIRM_BROKER_FLAT,
)


def protected_flatten_plan(
    *,
    atomic_flatten: bool = False,
    broker_atomic_flatten_documented: bool = False,
) -> tuple[FlattenStep, ...]:
    """Return the sanctioned flatten sequence for the requested mode.

    The default mode keeps the protective stop active until the broker
    confirms flat, then cancels the remaining OCO leg. This is the only
    sanctioned sequence unless the broker has a documented atomic
    flatten (see ``docs/PROCUREMENT.md`` row "OCO residence confirm").
    """
    if atomic_flatten:
        if not broker_atomic_flatten_documented:
            raise FlattenSequenceError(
                "atomic_flatten requires broker_atomic_flatten_documented=True; "
                "the documented broker/OCO confirmation must record a "
                "broker-native atomic flatten path. Default sequence "
                "(cancel-after-flatten) is the only sanctioned alternative."
            )
        return ATOMIC_FLATTEN_SEQUENCE
    return DEFAULT_FLATTEN_SEQUENCE


def validate_flatten_plan(
    plan: tuple[FlattenStep, ...],
    *,
    atomic_flatten: bool = False,
) -> None:
    """Reject any plan that cancels protective stops before broker confirms flat,
    unless ``atomic_flatten`` is set and the plan uses ATOMIC_FLATTEN.

    Raises :class:`FlattenSequenceError` on any violation.
    """
    if not plan:
        raise FlattenSequenceError("flatten plan must not be empty")

    if FlattenStep.HALT_NEW_ENTRIES not in plan:
        raise FlattenSequenceError("plan missing HALT_NEW_ENTRIES")
    if FlattenStep.CONFIRM_BROKER_FLAT not in plan:
        raise FlattenSequenceError("plan missing CONFIRM_BROKER_FLAT")
    if plan.index(FlattenStep.HALT_NEW_ENTRIES) != 0:
        raise FlattenSequenceError("HALT_NEW_ENTRIES must be the first step")

    if atomic_flatten:
        if FlattenStep.ATOMIC_FLATTEN not in plan:
            raise FlattenSequenceError(
                "atomic_flatten=True but plan does not include ATOMIC_FLATTEN"
            )
        if FlattenStep.CANCEL_REMAINING_OCO in plan:
            raise FlattenSequenceError(
                "atomic_flatten plan must not include CANCEL_REMAINING_OCO; "
                "the broker-native atomic call owns the cancel"
            )
        if FlattenStep.SUBMIT_MARKET_FLATTEN in plan:
            raise FlattenSequenceError(
                "atomic_flatten plan must not include SUBMIT_MARKET_FLATTEN; "
                "atomic call replaces the manual flatten"
            )
        return

    if FlattenStep.KEEP_STOP_ACTIVE not in plan:
        raise FlattenSequenceError(
            "default plan must include KEEP_STOP_ACTIVE; cancel-first is "
            "rejected unless atomic_flatten=True"
        )
    if FlattenStep.SUBMIT_MARKET_FLATTEN not in plan:
        raise FlattenSequenceError("default plan must include SUBMIT_MARKET_FLATTEN")

    keep_idx = plan.index(FlattenStep.KEEP_STOP_ACTIVE)
    flatten_idx = plan.index(FlattenStep.SUBMIT_MARKET_FLATTEN)
    confirm_idx = plan.index(FlattenStep.CONFIRM_BROKER_FLAT)

    if not (keep_idx < flatten_idx):
        raise FlattenSequenceError(
            "KEEP_STOP_ACTIVE must precede SUBMIT_MARKET_FLATTEN"
        )
    if not (flatten_idx < confirm_idx):
        raise FlattenSequenceError(
            "SUBMIT_MARKET_FLATTEN must precede CONFIRM_BROKER_FLAT"
        )

    if FlattenStep.CANCEL_REMAINING_OCO in plan:
        cancel_idx = plan.index(FlattenStep.CANCEL_REMAINING_OCO)
        if not (confirm_idx < cancel_idx):
            raise FlattenSequenceError(
                "CANCEL_REMAINING_OCO must come AFTER CONFIRM_BROKER_FLAT — "
                "cancel-before-flatten is forbidden unless atomic_flatten=True"
            )
