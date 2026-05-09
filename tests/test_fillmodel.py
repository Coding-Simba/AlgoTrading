from algotrading.bars import Bar, FIVE_MIN
from algotrading.fillmodel import (
    D2_PLACEHOLDER_TAG,
    FillModel,
    OrderIntent,
    OrderSide,
    OrderType,
    PlaceholderCosts,
)
from algotrading.ingestion.types import Tick


def _tick(ts_ns: int, price: int) -> Tick:
    return Tick(ts_ns=ts_ns, symbol="MES", price=price, size=1, aggressor="U")


def _bar(open_p: int, high: int, low: int, close: int) -> Bar:
    return Bar(
        open_ns=0, close_ns=FIVE_MIN,
        open=open_p, high=high, low=low, close=close,
        volume=10, tick_count=10, interval_ns=FIVE_MIN,
    )


def test_market_buy_applies_slippage() -> None:
    fm = FillModel(PlaceholderCosts(slippage_ticks=2))
    res = fm.fill_market(OrderIntent(OrderSide.BUY, 1, OrderType.MARKET), _tick(100, 4500))
    assert res.filled and res.fill_price == 4502
    assert res.cost_tag == D2_PLACEHOLDER_TAG
    assert res.is_placeholder()


def test_limit_buy_fills_when_price_at_or_below() -> None:
    fm = FillModel()
    intent = OrderIntent(OrderSide.BUY, 1, OrderType.LIMIT, price=4500)
    assert fm.fill_limit_on_tick(intent, _tick(100, 4501)) is None
    res = fm.fill_limit_on_tick(intent, _tick(101, 4500))
    assert res is not None and res.filled and res.fill_price == 4500


def test_stop_triggered_on_print_through() -> None:
    fm = FillModel()
    intent = OrderIntent(OrderSide.BUY, 1, OrderType.STOP, price=4505)
    assert not fm.stop_triggered(intent, _tick(100, 4504))
    assert fm.stop_triggered(intent, _tick(101, 4505))


def test_stop_fill_records_slippage() -> None:
    fm = FillModel(PlaceholderCosts(slippage_ticks=1))
    intent = OrderIntent(OrderSide.SELL, 1, OrderType.STOP, price=4495)
    res = fm.fill_stop_on_tick(intent, _tick(100, 4495))
    assert res is not None and res.filled
    assert res.fill_price == 4494


def test_intrabar_collision_marked_ambiguous_and_uses_stop() -> None:
    fm = FillModel(costs=None)
    bar = _bar(open_p=4500, high=4520, low=4480, close=4500)
    res = fm.resolve_bracket_on_bar(
        side=OrderSide.BUY, qty=1,
        stop_loss=4490, take_profit=4510, bar=bar,
    )
    assert res.filled
    assert res.ambiguous_collision is True
    assert res.fill_price == 4490
    assert "ambiguous_collision" in res.notes


def test_target_only_hit_no_collision() -> None:
    fm = FillModel(costs=None)
    bar = _bar(open_p=4500, high=4520, low=4495, close=4515)
    res = fm.resolve_bracket_on_bar(
        side=OrderSide.BUY, qty=1, stop_loss=4490, take_profit=4510, bar=bar,
    )
    assert res.filled and not res.ambiguous_collision
    assert res.fill_price == 4510


def test_stop_only_hit_no_collision() -> None:
    fm = FillModel(costs=None)
    bar = _bar(open_p=4500, high=4505, low=4480, close=4495)
    res = fm.resolve_bracket_on_bar(
        side=OrderSide.BUY, qty=1, stop_loss=4490, take_profit=4510, bar=bar,
    )
    assert res.filled and not res.ambiguous_collision
    assert res.fill_price == 4490


def test_no_levels_hit_unfilled() -> None:
    fm = FillModel(costs=None)
    bar = _bar(open_p=4500, high=4505, low=4495, close=4502)
    res = fm.resolve_bracket_on_bar(
        side=OrderSide.BUY, qty=1, stop_loss=4490, take_profit=4510, bar=bar,
    )
    assert not res.filled


def test_costs_none_disables_placeholder_tag() -> None:
    fm = FillModel(costs=None)
    res = fm.fill_market(OrderIntent(OrderSide.BUY, 1, OrderType.MARKET), _tick(100, 4500))
    assert res.cost_tag == ""
    assert not res.is_placeholder()
