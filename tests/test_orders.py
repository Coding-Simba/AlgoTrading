import pytest

from algotrading.orders import (
    OrderRecord,
    OrderState,
    OrderStateError,
    OrderStateMachine,
)


def test_happy_path_full_fill() -> None:
    rec = OrderRecord(order_id="o1", qty_total=2)
    sm = OrderStateMachine(rec)
    sm.submit(1)
    sm.ack(2)
    sm.fill(3, 1)
    assert rec.state is OrderState.PARTIAL_FILL
    sm.fill(4, 1)
    assert rec.state is OrderState.FILLED
    assert rec.is_terminal()


def test_cancel_after_partial() -> None:
    rec = OrderRecord(order_id="o2", qty_total=2)
    sm = OrderStateMachine(rec)
    sm.submit(1)
    sm.ack(2)
    sm.fill(3, 1)
    sm.cancel(4)
    assert rec.state is OrderState.CANCELED


def test_cannot_transition_from_terminal() -> None:
    rec = OrderRecord(order_id="o3", qty_total=1)
    sm = OrderStateMachine(rec)
    sm.submit(1)
    sm.ack(2)
    sm.fill(3, 1)
    with pytest.raises(OrderStateError):
        sm.cancel(4)
    with pytest.raises(OrderStateError):
        sm.expire(5)


def test_overfill_rejected() -> None:
    rec = OrderRecord(order_id="o4", qty_total=1)
    sm = OrderStateMachine(rec)
    sm.submit(1)
    sm.ack(2)
    with pytest.raises(OrderStateError):
        sm.fill(3, 2)


def test_reject_from_pending_new() -> None:
    rec = OrderRecord(order_id="o5", qty_total=1)
    sm = OrderStateMachine(rec)
    sm.submit(1)
    sm.reject(2)
    assert rec.state is OrderState.REJECTED


def test_invalid_transition_ack_before_submit() -> None:
    rec = OrderRecord(order_id="o6", qty_total=1)
    sm = OrderStateMachine(rec)
    with pytest.raises(OrderStateError):
        sm.ack(1)


def test_history_recorded() -> None:
    rec = OrderRecord(order_id="o7", qty_total=1)
    sm = OrderStateMachine(rec)
    sm.submit(1)
    sm.ack(2)
    sm.fill(3, 1)
    states = [h[2] for h in rec.history]
    assert states == [OrderState.PENDING_NEW, OrderState.WORKING, OrderState.FILLED]
