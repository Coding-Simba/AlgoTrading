import io

import pytest

from algotrading.ingestion import (
    BBOQuote,
    IngestionError,
    Tick,
    iter_bbo,
    iter_ticks,
    parse_bbo_line,
    parse_tick_line,
)


def test_tick_parse_round_trip() -> None:
    row = {"ts_ns": "100", "symbol": "MES", "price": "4500", "size": "1", "aggressor": "B"}
    t = parse_tick_line(row)
    assert t == Tick(ts_ns=100, symbol="MES", price=4500, size=1, aggressor="B")


def test_tick_invalid_aggressor() -> None:
    row = {"ts_ns": "100", "symbol": "MES", "price": "4500", "size": "1", "aggressor": "X"}
    with pytest.raises(IngestionError):
        parse_tick_line(row)


def test_bbo_crossed_book_with_zero_sizes_allowed() -> None:
    q = parse_bbo_line({
        "ts_ns": "1", "symbol": "MES", "bid_px": "10", "bid_sz": "0", "ask_px": "9", "ask_sz": "0",
    })
    assert q.bid_px == 10 and q.ask_px == 9


def test_bbo_crossed_book_with_nonzero_size_rejected() -> None:
    with pytest.raises(IngestionError):
        parse_bbo_line({
            "ts_ns": "1", "symbol": "MES", "bid_px": "10", "bid_sz": "1", "ask_px": "9", "ask_sz": "1",
        })


def test_iter_ticks_monotonic() -> None:
    csv_in = (
        "ts_ns,symbol,price,size,aggressor\n"
        "100,MES,4500,1,B\n"
        "200,MES,4501,2,S\n"
    )
    ticks = list(iter_ticks(io.StringIO(csv_in)))
    assert [t.ts_ns for t in ticks] == [100, 200]


def test_iter_ticks_rejects_non_monotonic() -> None:
    csv_in = (
        "ts_ns,symbol,price,size,aggressor\n"
        "200,MES,4500,1,B\n"
        "100,MES,4501,2,S\n"
    )
    with pytest.raises(IngestionError):
        list(iter_ticks(io.StringIO(csv_in)))


def test_iter_bbo() -> None:
    csv_in = (
        "ts_ns,symbol,bid_px,bid_sz,ask_px,ask_sz\n"
        "100,MES,4500,1,4501,1\n"
        "150,MES,4500,2,4501,3\n"
    )
    quotes = list(iter_bbo(io.StringIO(csv_in)))
    assert quotes[0] == BBOQuote(100, "MES", 4500, 1, 4501, 1)
    assert quotes[1].bid_sz == 2
