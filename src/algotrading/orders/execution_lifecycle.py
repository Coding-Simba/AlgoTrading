"""Execution lifecycle (per Appendix H §1.b).

The execution lifecycle is the state of a *single trade attempt* — from
signal generation to flat reconciliation. It is distinct from the
strategy-version lifecycle (REGISTERED / STANDBY / ACTIVE / ...) which
governs whether a strategy is allowed to emit signals at all, and from
the order-level lifecycle (NEW / PENDING_NEW / WORKING / ...) in
``state_machine.py`` which tracks individual broker orders. See
``docs/appendices/H_execution_ops.md`` §1 for the mapping.

Allowed transitions are explicit; any other transition raises
``ExecutionStateError``. ERROR_HALTED is reachable from any non-terminal
state via ``transition_to_error``; exit from ERROR_HALTED requires an
explicit manual-review reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExecutionStateError(RuntimeError):
    pass


class ExecutionState(str, Enum):
    FLAT = "flat"
    SIGNAL_PENDING = "signal_pending"
    ENTRY_SENT = "entry_sent"
    ENTRY_FILLED = "entry_filled"
    BRACKET_PENDING = "bracket_pending"
    POSITION_PROTECTED = "position_protected"
    EXIT_PENDING = "exit_pending"
    FLAT_RECONCILING = "flat_reconciling"
    ERROR_HALTED = "error_halted"


_ALLOWED: dict[ExecutionState, frozenset[ExecutionState]] = {
    ExecutionState.FLAT:               frozenset({ExecutionState.SIGNAL_PENDING}),
    ExecutionState.SIGNAL_PENDING:     frozenset({ExecutionState.ENTRY_SENT, ExecutionState.FLAT}),
    ExecutionState.ENTRY_SENT:         frozenset({ExecutionState.ENTRY_FILLED, ExecutionState.FLAT}),
    ExecutionState.ENTRY_FILLED:       frozenset({ExecutionState.BRACKET_PENDING}),
    ExecutionState.BRACKET_PENDING:    frozenset({ExecutionState.POSITION_PROTECTED, ExecutionState.EXIT_PENDING}),
    ExecutionState.POSITION_PROTECTED: frozenset({ExecutionState.EXIT_PENDING}),
    ExecutionState.EXIT_PENDING:       frozenset({ExecutionState.FLAT_RECONCILING}),
    ExecutionState.FLAT_RECONCILING:   frozenset({ExecutionState.FLAT}),
    ExecutionState.ERROR_HALTED:       frozenset({ExecutionState.FLAT}),
}


_ENTRY_FORBIDDEN_OUTSIDE_FLAT = (
    ExecutionState.SIGNAL_PENDING,
    ExecutionState.ENTRY_SENT,
    ExecutionState.ENTRY_FILLED,
    ExecutionState.BRACKET_PENDING,
    ExecutionState.POSITION_PROTECTED,
    ExecutionState.EXIT_PENDING,
    ExecutionState.FLAT_RECONCILING,
    ExecutionState.ERROR_HALTED,
)


@dataclass
class ExecutionLifecycle:
    state: ExecutionState = ExecutionState.FLAT
    history: list[tuple[int, ExecutionState, str]] = field(default_factory=list)

    def can_emit_entry(self) -> bool:
        return self.state == ExecutionState.FLAT

    def transition(self, ts_ns: int, target: ExecutionState, *, reason: str = "") -> None:
        if self.state == ExecutionState.ERROR_HALTED and target == ExecutionState.FLAT:
            if "manual_review" not in reason.lower():
                raise ExecutionStateError(
                    "ERROR_HALTED -> FLAT requires manual review (reason must "
                    "include 'manual_review')"
                )
            self._record(ts_ns, target, reason)
            return

        if target == ExecutionState.SIGNAL_PENDING and self.state in _ENTRY_FORBIDDEN_OUTSIDE_FLAT:
            raise ExecutionStateError(
                f"new entry rejected: SIGNAL_PENDING only allowed from FLAT, "
                f"current state is {self.state.value}"
            )

        if target not in _ALLOWED[self.state]:
            raise ExecutionStateError(
                f"invalid execution transition {self.state.value} -> {target.value} "
                f"(reason: {reason or 'none'})"
            )
        self._record(ts_ns, target, reason)

    def transition_to_error(self, ts_ns: int, *, reason: str) -> None:
        if not reason.strip():
            raise ExecutionStateError("ERROR_HALTED requires a non-empty reason")
        if self.state == ExecutionState.ERROR_HALTED:
            raise ExecutionStateError("already in ERROR_HALTED")
        self._record(ts_ns, ExecutionState.ERROR_HALTED, reason)

    def _record(self, ts_ns: int, target: ExecutionState, reason: str) -> None:
        self.state = target
        self.history.append((ts_ns, target, reason))
