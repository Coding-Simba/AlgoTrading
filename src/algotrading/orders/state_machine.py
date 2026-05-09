"""Order state-machine simulator (per §H.2).

States:

    NEW -> PENDING_NEW -> WORKING -> [PARTIAL_FILL] -> FILLED
                                  -> CANCELED
                                  -> REJECTED
                                  -> EXPIRED

Allowed transitions are explicit; any other transition raises
``OrderStateError``. The state machine is event-driven: callers send
``OrderEvent`` instances and read the updated ``OrderRecord``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OrderStateError(RuntimeError):
    pass


class OrderState(str, Enum):
    NEW = "new"
    PENDING_NEW = "pending_new"
    WORKING = "working"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


_TERMINAL: frozenset[OrderState] = frozenset({
    OrderState.FILLED,
    OrderState.CANCELED,
    OrderState.REJECTED,
    OrderState.EXPIRED,
})


_ALLOWED: dict[OrderState, frozenset[OrderState]] = {
    OrderState.NEW:          frozenset({OrderState.PENDING_NEW, OrderState.REJECTED}),
    OrderState.PENDING_NEW:  frozenset({OrderState.WORKING, OrderState.REJECTED}),
    OrderState.WORKING:      frozenset({
        OrderState.PARTIAL_FILL, OrderState.FILLED,
        OrderState.CANCELED, OrderState.EXPIRED,
    }),
    OrderState.PARTIAL_FILL: frozenset({
        OrderState.PARTIAL_FILL, OrderState.FILLED,
        OrderState.CANCELED, OrderState.EXPIRED,
    }),
    OrderState.FILLED:       frozenset(),
    OrderState.CANCELED:     frozenset(),
    OrderState.REJECTED:     frozenset(),
    OrderState.EXPIRED:      frozenset(),
}


class OrderEvent(str, Enum):
    SUBMIT = "submit"
    ACK = "ack"
    REJECT = "reject"
    PARTIAL_FILL = "partial"
    FILL = "fill"
    CANCEL = "cancel"
    EXPIRE = "expire"


@dataclass
class OrderRecord:
    order_id: str
    state: OrderState = OrderState.NEW
    qty_total: int = 0
    qty_filled: int = 0
    history: list[tuple[int, OrderEvent, OrderState]] = field(default_factory=list)

    def remaining(self) -> int:
        return self.qty_total - self.qty_filled

    def is_terminal(self) -> bool:
        return self.state in _TERMINAL


class OrderStateMachine:
    def __init__(self, record: OrderRecord) -> None:
        self.record = record

    def submit(self, ts_ns: int) -> None:
        self._transition(ts_ns, OrderEvent.SUBMIT, OrderState.PENDING_NEW)

    def ack(self, ts_ns: int) -> None:
        self._transition(ts_ns, OrderEvent.ACK, OrderState.WORKING)

    def reject(self, ts_ns: int) -> None:
        self._transition(ts_ns, OrderEvent.REJECT, OrderState.REJECTED)

    def cancel(self, ts_ns: int) -> None:
        self._transition(ts_ns, OrderEvent.CANCEL, OrderState.CANCELED)

    def expire(self, ts_ns: int) -> None:
        self._transition(ts_ns, OrderEvent.EXPIRE, OrderState.EXPIRED)

    def fill(self, ts_ns: int, qty: int) -> None:
        if qty <= 0:
            raise OrderStateError(f"fill qty must be positive, got {qty}")
        if qty > self.record.remaining():
            raise OrderStateError(
                f"fill qty {qty} exceeds remaining {self.record.remaining()}"
            )
        self.record.qty_filled += qty
        if self.record.qty_filled == self.record.qty_total:
            self._transition(ts_ns, OrderEvent.FILL, OrderState.FILLED)
        else:
            self._transition(ts_ns, OrderEvent.PARTIAL_FILL, OrderState.PARTIAL_FILL)

    def _transition(self, ts_ns: int, event: OrderEvent, target: OrderState) -> None:
        cur = self.record.state
        if cur in _TERMINAL:
            raise OrderStateError(
                f"cannot {event.value} from terminal state {cur.value}"
            )
        if target not in _ALLOWED[cur]:
            raise OrderStateError(
                f"invalid transition {cur.value} -> {target.value} on {event.value}"
            )
        self.record.state = target
        self.record.history.append((ts_ns, event, target))
