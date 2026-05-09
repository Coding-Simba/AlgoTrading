"""Latency / clock-drift monitoring scaffolding.

These monitors track:

- ``LatencyMonitor``     — per-event latency between two timestamps (e.g.,
  exchange-stamped tick vs. local-receive). Emits an alert above a
  configured threshold and tracks rolling p50/p95/p99.
- ``ClockDriftMonitor``  — local-vs-reference clock skew as a rolling mean.
  Emits an alert if drift crosses a configured magnitude.

Storage is in-memory and bounded; downstream wiring to a metrics sink is
deferred to Sprint 2.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass(frozen=True, slots=True)
class MonitorAlert:
    name: str
    ts_ns: int
    detail: str
    severity: str = "warn"


@dataclass
class LatencyMonitor:
    name: str
    window: int = 10_000
    warn_ns: int = 50_000_000
    critical_ns: int = 250_000_000
    samples: Deque[int] = field(default_factory=deque, init=False)
    alerts: list[MonitorAlert] = field(default_factory=list, init=False)

    def observe(self, exchange_ns: int, local_ns: int) -> int:
        latency = local_ns - exchange_ns
        if latency < 0:
            self.alerts.append(
                MonitorAlert(self.name, local_ns, f"negative latency {latency}", "critical")
            )
        self.samples.append(latency)
        while len(self.samples) > self.window:
            self.samples.popleft()
        if latency >= self.critical_ns:
            self.alerts.append(MonitorAlert(self.name, local_ns, f"latency {latency}ns", "critical"))
        elif latency >= self.warn_ns:
            self.alerts.append(MonitorAlert(self.name, local_ns, f"latency {latency}ns", "warn"))
        return latency

    def percentile(self, p: float) -> int | None:
        if not self.samples:
            return None
        if not 0.0 < p < 1.0:
            raise ValueError("p must be in (0, 1)")
        sorted_samples = sorted(self.samples)
        idx = min(len(sorted_samples) - 1, max(0, int(round(p * (len(sorted_samples) - 1)))))
        return sorted_samples[idx]


@dataclass
class ClockDriftMonitor:
    name: str
    window: int = 1_000
    # Defaults aligned to the signed spec: critical_ns is the halt-new-entries
    # threshold (250 ms). Operational early-warning is at 10 ms. Stricter
    # operational thresholds require Director Sponsor and Risk Reviewer
    # approval recorded in configs/risk_limits.yml notes.
    warn_ns: int = 10_000_000          # 10ms
    critical_ns: int = 250_000_000     # 250ms — spec halt threshold
    samples: Deque[int] = field(default_factory=deque, init=False)
    alerts: list[MonitorAlert] = field(default_factory=list, init=False)

    def observe(self, local_ns: int, reference_ns: int) -> int:
        drift = local_ns - reference_ns
        self.samples.append(drift)
        while len(self.samples) > self.window:
            self.samples.popleft()
        mag = abs(drift)
        if mag >= self.critical_ns:
            self.alerts.append(
                MonitorAlert(self.name, local_ns, f"clock drift {drift}ns", "critical")
            )
        elif mag >= self.warn_ns:
            self.alerts.append(
                MonitorAlert(self.name, local_ns, f"clock drift {drift}ns", "warn")
            )
        return drift

    def rolling_mean(self) -> float | None:
        if not self.samples:
            return None
        return sum(self.samples) / len(self.samples)
