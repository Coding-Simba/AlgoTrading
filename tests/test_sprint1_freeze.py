"""Sprint 1 freeze guard.

The errata §10 forbids v0.2 signal logic, B.7 / B.8 entry rules, and EMA /
VWAP / ATR wired to v0.2 in this sprint. This test scans the source tree for
forbidden symbols and patterns. It does **not** prevent legitimate
documentation references (which is why string occurrences inside ``docs/``
are exempt).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_ROOT = _REPO_ROOT / "src"


_FORBIDDEN_PATTERNS = [
    re.compile(r"\bclass\s+V0_?2[A-Za-z_]*Strategy\b"),
    re.compile(r"\bdef\s+v0_?2_[a-z_]*signal\b"),
    re.compile(r"\bb_?7_entry\b", re.IGNORECASE),
    re.compile(r"\bb_?8_entry\b", re.IGNORECASE),
    re.compile(r"\bcompute_ema_signal\b"),
    re.compile(r"\bcompute_vwap_signal\b"),
    re.compile(r"\bcompute_atr_signal\b"),
]


def _python_sources() -> list[Path]:
    return [p for p in _SRC_ROOT.rglob("*.py") if p.is_file()]


@pytest.mark.parametrize("pattern", _FORBIDDEN_PATTERNS, ids=lambda p: p.pattern)
def test_no_forbidden_v02_logic(pattern: re.Pattern[str]) -> None:
    offenders: list[str] = []
    for src in _python_sources():
        text = src.read_text(encoding="utf-8")
        if pattern.search(text):
            offenders.append(str(src.relative_to(_REPO_ROOT)))
    assert not offenders, f"forbidden v0.2 pattern {pattern.pattern} found in {offenders}"


def test_baselines_module_does_not_import_indicators() -> None:
    forbidden = ("ema", "vwap", "atr")
    for src in (_SRC_ROOT / "algotrading" / "baselines").rglob("*.py"):
        text = src.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text, f"{src} mentions {token!r}"
