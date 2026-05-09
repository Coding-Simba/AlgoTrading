"""Kill-switch framework per Appendix H §1.e.

The kill switch consumes Director-set risk values
(`configs/risk_limits.yml`) and the monitoring streams. When triggered,
it drives the execution lifecycle to ERROR_HALTED and invokes the
protected-flatten plan (see ``orders.flatten``).

This module provides the trigger surface; the runner wires it to a
broker adapter (mock or live) and to the protected-flatten executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class TriggerReason(str, Enum):
    DAILY_LOSS_LIMIT_HIT = "daily_loss_limit_hit"
    LOSING_STREAK_THRESHOLD = "losing_streak_threshold"
    DRAWDOWN_CEILING_BREACH = "drawdown_ceiling_breach"
    CLOCK_DRIFT_CRITICAL = "clock_drift_critical"
    LATENCY_CRITICAL_SUSTAINED = "latency_critical_sustained"
    MANUAL_OPERATOR_TRIP = "manual_operator_trip"
    LIFECYCLE_MAPPING_VIOLATION = "lifecycle_mapping_violation"


@dataclass(frozen=True)
class KillSwitchTrigger:
    reason: TriggerReason
    detail: str
    ts_ns: int


@dataclass
class KillSwitch:
    armed: bool = True
    triggers: list[KillSwitchTrigger] = field(default_factory=list)

    def trip(self, reason: TriggerReason, *, detail: str, ts_ns: int) -> None:
        if not self.armed:
            return
        self.triggers.append(KillSwitchTrigger(reason=reason, detail=detail, ts_ns=ts_ns))

    def disarm(self) -> None:
        self.armed = False

    def rearm(self) -> None:
        self.armed = True
        self.triggers.clear()
