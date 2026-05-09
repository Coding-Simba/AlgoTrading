"""Session counters used by the v0.2 strategy (max 3 trades, one open
position at a time, 15:58 ET forced flatten).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SessionCounters:
    trades_entered_today: int = 0
    open_positions: int = 0

    def can_enter(self) -> bool:
        return self.trades_entered_today < 3 and self.open_positions == 0

    def on_entry(self) -> None:
        self.trades_entered_today += 1
        self.open_positions += 1

    def on_exit(self) -> None:
        if self.open_positions > 0:
            self.open_positions -= 1


@dataclass
class SessionState:
    """Per-RTH-session view used by the strategy. Counters reset at
    session open by the calling runner."""

    session_date: str  # "YYYY-MM-DD"
    counters: SessionCounters = field(default_factory=SessionCounters)
    error_halted: bool = False
