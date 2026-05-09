"""Real-cost model loaded from `configs/broker_rate_sheet.yml`.

Replaces :class:`PlaceholderCosts` once Ops signs the rate sheet
(errata §5). A `RateSheetCosts` instance produces fills with
``cost_tag=""`` (empty), so any fill stream sourced from it is **not**
rejected by the approved-backtest guard.

Loader contract:
  - The file exists and parses as YAML.
  - ``signed: true`` and ``signed_by`` / ``signed_at_iso`` are populated.
  - Every numeric line item is present, ``>= 0``, and integer-valued in
    USD-cents.
  - ``all_in_per_side_usd_cents`` equals the sum of the four component
    line items.
  - ``all_in_round_trip_usd_cents`` equals 2 × per-side.

Failure on any condition raises :class:`RateSheetError`. Construction
is the only place we validate; downstream code can trust a returned
instance.

Cost reporting: the existing fill-model pipeline reports
``cost_ticks: int``. We convert per-side USD-cents to ticks by
``ceil(cents / tick_value_cents)`` so we never under-report costs.
This is conservative (slightly pessimistic) and avoids touching the
many call sites that read ``cost_ticks`` as an integer. A migration to
USD-cents native is tracked as a TODO in
`docs/broker/ninjatrader_integration.md`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

from .model import D2_PLACEHOLDER_TAG


class RateSheetError(RuntimeError):
    """Raised when the rate sheet config is missing, malformed, or unsigned."""


_REQUIRED_INSTRUMENT_KEYS: tuple[str, ...] = (
    "tick_size",
    "tick_value_usd_cents",
    "nt_commission_per_side_usd_cents",
    "cme_exchange_fee_per_side_usd_cents",
    "nfa_assessment_per_side_usd_cents",
    "clearing_fee_per_side_usd_cents",
    "routing_fee_per_side_usd_cents",
    "all_in_per_side_usd_cents",
    "all_in_round_trip_usd_cents",
)

_FEE_COMPONENTS: tuple[str, ...] = (
    "nt_commission_per_side_usd_cents",
    "cme_exchange_fee_per_side_usd_cents",
    "nfa_assessment_per_side_usd_cents",
    "clearing_fee_per_side_usd_cents",
    "routing_fee_per_side_usd_cents",
)


@dataclass(frozen=True)
class RateSheetCosts:
    """Real-cost model. Always emits ``cost_tag=""`` (no placeholder)."""

    instrument: str
    commission_per_side_usd_cents: int
    all_in_per_side_usd_cents: int
    tick_value_usd_cents: int
    slippage_ticks: int
    tag: str = ""  # never D2_PLACEHOLDER_TAG.

    @property
    def commission_per_side_ticks(self) -> int:
        """Conservative integer-tick conversion (round up)."""
        return math.ceil(self.all_in_per_side_usd_cents / self.tick_value_usd_cents)

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        instrument: str = "MES",
    ) -> "RateSheetCosts":
        p = Path(path)
        if not p.exists():
            raise RateSheetError(f"rate sheet not found at {p}")
        try:
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise RateSheetError(f"rate sheet at {p} is not valid YAML: {exc}") from exc
        if not isinstance(raw, dict):
            raise RateSheetError(f"rate sheet at {p} did not parse to a mapping")
        if not raw.get("signed"):
            raise RateSheetError(
                f"rate sheet at {p} is not signed; approved-cost backtests "
                "require Ops sign-off (errata §5)"
            )
        signed_by = raw.get("signed_by") or ""
        signed_at_iso = raw.get("signed_at_iso") or ""
        if not signed_by or not signed_at_iso:
            raise RateSheetError(
                f"rate sheet at {p} has signed=true but signed_by / "
                "signed_at_iso are blank"
            )
        instruments = raw.get("instruments") or {}
        if instrument not in instruments:
            raise RateSheetError(
                f"rate sheet at {p} has no entry for instrument {instrument!r}"
            )
        spec = instruments[instrument] or {}
        for key in _REQUIRED_INSTRUMENT_KEYS:
            if key not in spec:
                raise RateSheetError(
                    f"rate sheet {instrument} block is missing key {key!r}"
                )
        for key in _FEE_COMPONENTS + (
            "all_in_per_side_usd_cents",
            "all_in_round_trip_usd_cents",
            "tick_value_usd_cents",
        ):
            v = spec[key]
            if not isinstance(v, int) or v < 0:
                raise RateSheetError(
                    f"rate sheet {instrument}.{key} must be a non-negative int, "
                    f"got {v!r}"
                )
        component_sum = sum(spec[k] for k in _FEE_COMPONENTS)
        if component_sum != spec["all_in_per_side_usd_cents"]:
            raise RateSheetError(
                f"rate sheet {instrument}.all_in_per_side_usd_cents "
                f"({spec['all_in_per_side_usd_cents']}) does not match "
                f"sum of components ({component_sum})"
            )
        if spec["all_in_round_trip_usd_cents"] != 2 * spec["all_in_per_side_usd_cents"]:
            raise RateSheetError(
                f"rate sheet {instrument}.all_in_round_trip_usd_cents must "
                f"equal 2 × all_in_per_side_usd_cents"
            )
        slippage_block = raw.get("slippage") or {}
        slippage_ticks = slippage_block.get("ticks_per_side", 1)
        if not isinstance(slippage_ticks, int) or slippage_ticks < 0:
            raise RateSheetError(
                "rate sheet slippage.ticks_per_side must be a non-negative int"
            )
        return cls(
            instrument=instrument,
            commission_per_side_usd_cents=spec["nt_commission_per_side_usd_cents"],
            all_in_per_side_usd_cents=spec["all_in_per_side_usd_cents"],
            tick_value_usd_cents=spec["tick_value_usd_cents"],
            slippage_ticks=slippage_ticks,
        )


def is_rate_sheet_signed(path: str | Path) -> bool:
    """Cheap probe: does the file parse, claim signed=true, and carry
    a non-blank signer + timestamp? Does not validate inner consistency.
    Use :meth:`RateSheetCosts.load` for full validation."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return False
    if not isinstance(raw, dict):
        return False
    return (
        bool(raw.get("signed"))
        and bool(raw.get("signed_by"))
        and bool(raw.get("signed_at_iso"))
    )


__all__ = [
    "RateSheetCosts",
    "RateSheetError",
    "is_rate_sheet_signed",
    "D2_PLACEHOLDER_TAG",
]
