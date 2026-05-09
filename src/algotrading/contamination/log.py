"""Append-only research contamination log.

Implements the schema documented in
``docs/research_contamination_log/README.md``. Rows are RFC-4180 quoted as
needed. The CSV writer never edits or deletes existing rows; corrections are
new rows whose ``description`` references the original row's ``datetime_iso``
and ``researcher``.
"""

from __future__ import annotations

import csv
import io
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ALLOWED_ACTIONS = (
    "parameter_change",
    "rule_change",
    "variant_tested",
    "validation_query",
    "data_qa_check",
    "other",
)

ALLOWED_DATASETS = ("training", "validation", "live", "paper", "none")

ALLOWED_DECISIONS = ("kept", "discarded", "logged_for_next_version", "escalated")


HEADER = (
    "datetime_iso",
    "researcher",
    "strategy_version",
    "action_type",
    "description",
    "dataset_used",
    "result_observed",
    "decision",
    "reviewer_initials",
    "reviewer_date",
)


class ContaminationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LogRow:
    datetime_iso: str
    researcher: str
    strategy_version: str
    action_type: str
    description: str
    dataset_used: str
    result_observed: str
    decision: str
    reviewer_initials: str = ""
    reviewer_date: str = ""

    def validate(self) -> None:
        if self.action_type not in ALLOWED_ACTIONS:
            raise ContaminationError(f"action_type {self.action_type!r} not allowed")
        if self.dataset_used not in ALLOWED_DATASETS:
            raise ContaminationError(f"dataset_used {self.dataset_used!r} not allowed")
        if self.decision not in ALLOWED_DECISIONS:
            raise ContaminationError(f"decision {self.decision!r} not allowed")
        if not self.researcher:
            raise ContaminationError("researcher is required")
        if not self.strategy_version:
            raise ContaminationError("strategy_version is required")
        try:
            datetime.fromisoformat(self.datetime_iso)
        except ValueError as exc:
            raise ContaminationError(f"datetime_iso not ISO-8601: {self.datetime_iso!r}") from exc

    def to_tuple(self) -> tuple[str, ...]:
        return (
            self.datetime_iso,
            self.researcher,
            self.strategy_version,
            self.action_type,
            self.description,
            self.dataset_used,
            self.result_observed,
            self.decision,
            self.reviewer_initials,
            self.reviewer_date,
        )


@dataclass
class ContaminationLog:
    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            with self.path.open("w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(HEADER)

    def append(self, row: LogRow) -> None:
        row.validate()
        line = _format_row(row.to_tuple())
        with self.path.open("a", encoding="utf-8", newline="") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())

    def read_all(self) -> list[LogRow]:
        with self.path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
        if not rows:
            return []
        if tuple(rows[0]) != HEADER:
            raise ContaminationError(f"header mismatch: {rows[0]!r}")
        out: list[LogRow] = []
        for raw in rows[1:]:
            if len(raw) != len(HEADER):
                raise ContaminationError(f"malformed row: {raw!r}")
            out.append(LogRow(*raw))
        return out

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _format_row(values: Iterable[str]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerow(list(values))
    return buf.getvalue()


def validate_log(path: str | os.PathLike[str]) -> list[str]:
    log = ContaminationLog(Path(path))
    errors: list[str] = []
    try:
        rows = log.read_all()
    except ContaminationError as exc:
        return [str(exc)]
    for i, row in enumerate(rows, start=2):
        try:
            row.validate()
        except ContaminationError as exc:
            errors.append(f"line {i}: {exc}")
    return errors
