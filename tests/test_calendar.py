from pathlib import Path
import datetime as dt

import pytest

from algotrading.calendar import (
    CalendarError,
    SessionCalendar,
    SessionType,
    SessionWindow,
    load_calendar,
)


_NS = 1_000_000_000


def _ns(date_str: str) -> int:
    return int(dt.datetime.fromisoformat(date_str).timestamp() * _NS)


def test_load_default_calendar() -> None:
    cal = load_calendar(Path(__file__).parent.parent / "configs" / "sessions" / "mes.yml")
    assert cal.timezone == "America/New_York"
    inside = _ns("2026-05-11T10:00:00-04:00")
    assert cal.is_open(inside)
    outside = _ns("2026-05-11T08:00:00-04:00")
    assert not cal.is_open(outside)


def test_overlapping_windows_rejected() -> None:
    a = SessionWindow(open_ns=100, close_ns=200, session_type=SessionType.REGULAR, label="a")
    b = SessionWindow(open_ns=150, close_ns=250, session_type=SessionType.REGULAR, label="b")
    with pytest.raises(CalendarError):
        SessionCalendar(timezone="UTC", windows=[a, b])


def test_close_must_exceed_open() -> None:
    with pytest.raises(CalendarError):
        SessionWindow(open_ns=200, close_ns=100, session_type=SessionType.REGULAR)


def test_holiday_detection() -> None:
    cal = load_calendar(Path(__file__).parent.parent / "configs" / "sessions" / "mes.yml")
    holiday_ts = _ns("2026-11-26T12:00:00-05:00")
    assert cal.is_holiday(holiday_ts)
    assert not cal.is_open(holiday_ts)


def test_half_day_detection() -> None:
    cal = load_calendar(Path(__file__).parent.parent / "configs" / "sessions" / "mes.yml")
    half = _ns("2026-11-27T11:00:00-05:00")
    assert cal.is_half_day(half)
    assert cal.is_open(half)
    after_half = _ns("2026-11-27T14:00:00-05:00")
    assert not cal.is_open(after_half)


def test_next_close_after() -> None:
    cal = load_calendar(Path(__file__).parent.parent / "configs" / "sessions" / "mes.yml")
    t = _ns("2026-05-11T10:00:00-04:00")
    expected = _ns("2026-05-11T16:00:00-04:00")
    assert cal.next_close_after(t) == expected


def test_naive_datetime_rejected(tmp_path: Path) -> None:
    p = tmp_path / "bad.yml"
    p.write_text(
        "timezone: UTC\nwindows:\n  - type: regular\n    open: '2026-05-11T09:30:00'\n    close: '2026-05-11T16:00:00'\n",
        encoding="utf-8",
    )
    with pytest.raises(CalendarError):
        load_calendar(p)
