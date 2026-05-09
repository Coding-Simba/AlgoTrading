"""Session calendar with holiday and half-day handling.

Calendar is loaded from YAML so the data layer can be reviewed without code
changes. The default calendar config lives at `configs/sessions/mes.yml`.

A session is one of:

- ``regular``  — normal RTH window
- ``half_day`` — early close (e.g., day before US Thanksgiving)
- ``holiday``  — full closure
- ``overnight``— globex / ETH; closed flag is False but isolated from RTH

The calendar is intentionally tick-resolution agnostic. Bar builders ask:

- ``is_open(ts_ns)`` — True if any session window covers ``ts_ns``
- ``window_for(ts_ns)`` — the active SessionWindow
- ``next_close_after(ts_ns)`` — next session close (used for forced flatten)
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable

import yaml


class CalendarError(ValueError):
    """Raised on calendar configuration or query errors."""


class SessionType(str, Enum):
    REGULAR = "regular"
    HALF_DAY = "half_day"
    HOLIDAY = "holiday"
    OVERNIGHT = "overnight"


_NS_PER_S = 1_000_000_000


@dataclass(frozen=True, slots=True)
class SessionWindow:
    open_ns: int
    close_ns: int
    session_type: SessionType
    label: str = ""

    def __post_init__(self) -> None:
        if self.session_type is SessionType.HOLIDAY:
            return
        if self.close_ns <= self.open_ns:
            raise CalendarError(
                f"close_ns ({self.close_ns}) must exceed open_ns ({self.open_ns})"
            )

    def contains(self, ts_ns: int) -> bool:
        return self.open_ns <= ts_ns < self.close_ns


@dataclass
class SessionCalendar:
    timezone: str
    windows: list[SessionWindow] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.windows = sorted(self.windows, key=lambda w: w.open_ns)
        prev: SessionWindow | None = None
        for w in self.windows:
            if w.session_type is SessionType.HOLIDAY:
                continue
            if prev is not None and prev.session_type is not SessionType.HOLIDAY:
                if w.open_ns < prev.close_ns:
                    raise CalendarError(
                        f"overlapping windows: {prev.label} and {w.label}"
                    )
            prev = w

    def is_open(self, ts_ns: int) -> bool:
        return self.window_for(ts_ns) is not None

    def window_for(self, ts_ns: int) -> SessionWindow | None:
        for w in self.windows:
            if w.session_type is SessionType.HOLIDAY:
                continue
            if w.contains(ts_ns):
                return w
        return None

    def next_close_after(self, ts_ns: int) -> int | None:
        for w in self.windows:
            if w.session_type is SessionType.HOLIDAY:
                continue
            if w.close_ns > ts_ns:
                return w.close_ns
        return None

    def is_holiday(self, ts_ns: int) -> bool:
        d = _date_of(ts_ns)
        for w in self.windows:
            if w.session_type is SessionType.HOLIDAY and _date_of(w.open_ns) == d:
                return True
        return False

    def is_half_day(self, ts_ns: int) -> bool:
        w = self.window_for(ts_ns)
        return bool(w and w.session_type is SessionType.HALF_DAY)


def _date_of(ts_ns: int) -> _dt.date:
    return _dt.datetime.fromtimestamp(ts_ns / _NS_PER_S, tz=_dt.timezone.utc).date()


def load_calendar(path: str | Path) -> SessionCalendar:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise CalendarError(f"calendar root must be a mapping, got {type(raw).__name__}")
    tz = raw.get("timezone", "UTC")
    windows_raw: Iterable[dict] = raw.get("windows") or []
    windows: list[SessionWindow] = []
    for entry in windows_raw:
        try:
            session_type = SessionType(entry["type"])
        except (KeyError, ValueError) as exc:
            raise CalendarError(f"invalid session type in entry {entry!r}") from exc
        if session_type is SessionType.HOLIDAY:
            day = _parse_day(entry["date"])
            open_ns = _to_ns(_dt.datetime.combine(day, _dt.time.min, _dt.timezone.utc))
            close_ns = open_ns
        else:
            open_ns = _parse_iso_ns(entry["open"])
            close_ns = _parse_iso_ns(entry["close"])
        windows.append(
            SessionWindow(
                open_ns=open_ns,
                close_ns=close_ns,
                session_type=session_type,
                label=entry.get("label", ""),
            )
        )
    return SessionCalendar(timezone=tz, windows=windows)


def _parse_iso_ns(s: str) -> int:
    return _to_ns(_dt.datetime.fromisoformat(s))


def _parse_day(s: str) -> _dt.date:
    return _dt.date.fromisoformat(s)


def _to_ns(dt: _dt.datetime) -> int:
    if dt.tzinfo is None:
        raise CalendarError(f"naive datetime not allowed: {dt!r}")
    return int(dt.timestamp() * _NS_PER_S)
