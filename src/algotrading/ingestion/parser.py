"""Vendor-agnostic CSV parsers for tick and BBO data.

Real ingestion will dispatch by vendor; this skeleton accepts a canonical CSV
form so the rest of the framework can be exercised in unit tests without
external data.

Canonical tick CSV columns:
    ts_ns,symbol,price,size,aggressor

Canonical BBO CSV columns:
    ts_ns,symbol,bid_px,bid_sz,ask_px,ask_sz
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Iterator

from .types import BBOQuote, IngestionError, Tick


_TICK_FIELDS = ("ts_ns", "symbol", "price", "size", "aggressor")
_BBO_FIELDS = ("ts_ns", "symbol", "bid_px", "bid_sz", "ask_px", "ask_sz")


def parse_tick_line(row: dict[str, str]) -> Tick:
    _require_fields(row, _TICK_FIELDS)
    return Tick(
        ts_ns=int(row["ts_ns"]),
        symbol=row["symbol"],
        price=int(row["price"]),
        size=int(row["size"]),
        aggressor=row["aggressor"],
    )


def parse_bbo_line(row: dict[str, str]) -> BBOQuote:
    _require_fields(row, _BBO_FIELDS)
    return BBOQuote(
        ts_ns=int(row["ts_ns"]),
        symbol=row["symbol"],
        bid_px=int(row["bid_px"]),
        bid_sz=int(row["bid_sz"]),
        ask_px=int(row["ask_px"]),
        ask_sz=int(row["ask_sz"]),
    )


def iter_ticks(source: Path | Iterable[str]) -> Iterator[Tick]:
    yield from _iter_records(source, parse_tick_line, _TICK_FIELDS)


def iter_bbo(source: Path | Iterable[str]) -> Iterator[BBOQuote]:
    yield from _iter_records(source, parse_bbo_line, _BBO_FIELDS)


def _require_fields(row: dict[str, str], fields: tuple[str, ...]) -> None:
    missing = [f for f in fields if f not in row or row[f] == ""]
    if missing:
        raise IngestionError(f"missing fields: {missing} in row {row!r}")


def _iter_records(source, parse_fn, fields):
    if isinstance(source, (str, Path)):
        with Path(source).open("r", encoding="utf-8", newline="") as fh:
            yield from _read_csv(fh, parse_fn, fields)
    else:
        yield from _read_csv(source, parse_fn, fields)


def _read_csv(fh, parse_fn, fields):
    reader = csv.DictReader(fh)
    if reader.fieldnames is None:
        return
    missing = [f for f in fields if f not in reader.fieldnames]
    if missing:
        raise IngestionError(f"CSV header missing fields: {missing}")
    last_ts = -1
    for row in reader:
        rec = parse_fn(row)
        if rec.ts_ns < last_ts:
            raise IngestionError(
                f"non-monotonic timestamps: {rec.ts_ns} < {last_ts} in row {row!r}"
            )
        last_ts = rec.ts_ns
        yield rec
