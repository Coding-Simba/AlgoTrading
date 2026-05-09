"""Tick and BBO record types.

Times are stored as UTC nanoseconds since epoch (int) to avoid floating-point
imprecision around bar boundaries (§B.5). Conversion to wall clock happens
only at the calendar / report layer.
"""

from __future__ import annotations

from dataclasses import dataclass


class IngestionError(ValueError):
    """Raised on malformed ingestion input."""


@dataclass(frozen=True, slots=True)
class Tick:
    ts_ns: int          # exchange timestamp, ns since UTC epoch
    symbol: str
    price: int          # price in ticks (integer) to avoid float drift
    size: int
    aggressor: str      # "B" (buy), "S" (sell), or "U" (unknown)

    def __post_init__(self) -> None:
        if self.ts_ns < 0:
            raise IngestionError(f"negative ts_ns: {self.ts_ns}")
        if self.size <= 0:
            raise IngestionError(f"non-positive size: {self.size}")
        if self.aggressor not in ("B", "S", "U"):
            raise IngestionError(f"invalid aggressor: {self.aggressor!r}")


@dataclass(frozen=True, slots=True)
class BBOQuote:
    ts_ns: int
    symbol: str
    bid_px: int
    bid_sz: int
    ask_px: int
    ask_sz: int

    def __post_init__(self) -> None:
        if self.ts_ns < 0:
            raise IngestionError(f"negative ts_ns: {self.ts_ns}")
        if self.bid_sz < 0 or self.ask_sz < 0:
            raise IngestionError("negative size in BBO")
        if self.bid_px > self.ask_px:
            if self.bid_sz != 0 or self.ask_sz != 0:
                raise IngestionError(
                    f"crossed book with non-zero sizes: bid {self.bid_px}/{self.bid_sz} "
                    f"ask {self.ask_px}/{self.ask_sz}"
                )
