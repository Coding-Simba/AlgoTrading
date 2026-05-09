from algotrading.indicators import ema, ema_seed, wilder_atr, session_vwap


def test_ema_seed_simple_average() -> None:
    seed = ema_seed([1.0, 2.0, 3.0, 4.0, 5.0], period=5)
    assert seed == 3.0


def test_ema_recurrence_after_seed() -> None:
    out = ema([1.0, 1.0, 1.0, 1.0, 1.0, 2.0], period=5)
    assert out[4] == 1.0
    assert out[5] is not None
    assert abs(out[5] - 4 / 3) < 1e-9


def test_ema_period_too_long_returns_none_series() -> None:
    out = ema([1.0, 2.0], period=5)
    assert out == [None, None]


def test_wilder_atr_constant_high_low_zero() -> None:
    out = wilder_atr([1] * 20, [1] * 20, [1] * 20, period=14)
    for v in out[14:]:
        assert v == 0.0


def test_wilder_atr_first_value_index() -> None:
    out = wilder_atr(
        highs=[10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
        lows=[8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27],
        closes=[9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28],
        period=14,
    )
    assert all(v is None for v in out[:14])
    assert out[14] is not None


def test_session_vwap_resets_at_session_start() -> None:
    prices = [10, 11, 12, 20, 21, 22]
    volumes = [1, 1, 1, 1, 1, 1]
    out = session_vwap(prices, volumes, [0, 3])
    assert abs(out[2] - 11) < 1e-9
    assert abs(out[5] - 21) < 1e-9
