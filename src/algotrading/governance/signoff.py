"""Sign-off matrix loader and gate-blocking guard.

Per docs/GATES.md and the v1.4-r1 errata §3, five pre-code sign-offs
(Appendices B, C, D, E, H) must be signed before any v0.2 strategy code
lands. Subsequent phase gates (broker rate sheet, Appendix F, validation
freeze, paper, small-size live, Appendix G) are signed at later phases and
are tracked in the same matrix so a single source of truth governs CI.

The guard refuses by default. There is no override flag — bypassing it
requires a Change Request reviewed by the Risk Reviewer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

import yaml


_VALID_GATES = (
    "v0.2_code",
    "v0.2_backtest",
    "validation",
    "paper",
    "live",
    "scaleup",
)


class SignoffError(RuntimeError):
    """Raised when a sign-off matrix row is missing, malformed, or unsigned
    for the requested gate."""


@dataclass(frozen=True)
class SignoffRow:
    id: str
    title: str
    signer_role: str
    required_for: str
    signed: bool
    signed_by: str
    signed_at_iso: str
    notes: str = ""


@dataclass
class SignoffMatrix:
    path: Path
    rows: list[SignoffRow] = field(default_factory=list)

    def rows_for_gate(self, gate: str) -> list[SignoffRow]:
        return [r for r in self.rows if r.required_for == gate]

    def find(self, row_id: str) -> SignoffRow | None:
        for r in self.rows:
            if r.id == row_id:
                return r
        return None


def _coerce_row(raw: dict) -> SignoffRow:
    if not isinstance(raw, dict):
        raise SignoffError(f"sign-off row must be a mapping, got {type(raw).__name__}")
    try:
        row = SignoffRow(
            id=str(raw["id"]),
            title=str(raw["title"]),
            signer_role=str(raw["signer_role"]),
            required_for=str(raw["required_for"]),
            signed=bool(raw.get("signed", False)),
            signed_by=str(raw.get("signed_by") or ""),
            signed_at_iso=str(raw.get("signed_at_iso") or ""),
            notes=str(raw.get("notes") or ""),
        )
    except KeyError as exc:
        raise SignoffError(f"sign-off row missing required field: {exc.args[0]}") from exc
    if row.required_for not in _VALID_GATES:
        raise SignoffError(
            f"sign-off row {row.id!r}: required_for {row.required_for!r} "
            f"not in {_VALID_GATES}"
        )
    return row


def load_matrix(path: str | Path) -> SignoffMatrix:
    p = Path(path)
    if not p.exists():
        raise SignoffError(f"sign-off matrix not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SignoffError(f"sign-off matrix root must be a mapping: {p}")
    rows_raw = raw.get("rows")
    if not isinstance(rows_raw, list) or not rows_raw:
        raise SignoffError(f"sign-off matrix has no rows: {p}")
    rows = [_coerce_row(r) for r in rows_raw]
    seen: set[str] = set()
    for r in rows:
        if r.id in seen:
            raise SignoffError(f"duplicate sign-off row id: {r.id}")
        seen.add(r.id)
    return SignoffMatrix(path=p, rows=rows)


def _is_iso8601(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _row_is_signed(row: SignoffRow) -> bool:
    return (
        row.signed
        and bool(row.signed_by.strip())
        and _is_iso8601(row.signed_at_iso)
    )


def require_signed(matrix: SignoffMatrix, *, gate: str) -> None:
    if gate not in _VALID_GATES:
        raise SignoffError(f"unknown gate {gate!r}; expected one of {_VALID_GATES}")
    relevant = matrix.rows_for_gate(gate)
    if not relevant:
        raise SignoffError(f"no sign-off rows declared for gate {gate!r}")
    unsigned: list[str] = []
    bad_signer: list[str] = []
    bad_date: list[str] = []
    for r in relevant:
        if not r.signed:
            unsigned.append(r.id)
            continue
        if not r.signed_by.strip():
            bad_signer.append(r.id)
            continue
        if not _is_iso8601(r.signed_at_iso):
            bad_date.append(r.id)
            continue
    problems: list[str] = []
    if unsigned:
        problems.append(f"unsigned rows: {sorted(unsigned)}")
    if bad_signer:
        problems.append(f"missing signed_by: {sorted(bad_signer)}")
    if bad_date:
        problems.append(f"unparseable signed_at_iso: {sorted(bad_date)}")
    if problems:
        raise SignoffError(
            f"sign-off matrix at {matrix.path} blocks gate {gate!r}: "
            + "; ".join(problems)
        )


def assert_v02_code_unblocked(matrix_path: str | Path) -> None:
    matrix = load_matrix(matrix_path)
    require_signed(matrix, gate="v0.2_code")


def iter_unsigned(matrix: SignoffMatrix, *, gate: str) -> Iterable[SignoffRow]:
    for r in matrix.rows_for_gate(gate):
        if not _row_is_signed(r):
            yield r
