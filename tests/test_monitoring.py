from algotrading.monitoring import ClockDriftMonitor, LatencyMonitor


def test_latency_warn_and_critical() -> None:
    m = LatencyMonitor(name="ingest", warn_ns=100, critical_ns=1000)
    m.observe(0, 50)
    m.observe(0, 200)
    m.observe(0, 1500)
    m.observe(0, 50)
    severities = [a.severity for a in m.alerts]
    assert "warn" in severities
    assert "critical" in severities


def test_latency_negative_alerts_critical() -> None:
    m = LatencyMonitor(name="ingest")
    m.observe(100, 50)
    assert any(a.severity == "critical" for a in m.alerts)


def test_latency_percentile_after_samples() -> None:
    m = LatencyMonitor(name="ingest", warn_ns=10**12, critical_ns=10**12, window=100)
    for v in range(100):
        m.observe(0, v)
    p50 = m.percentile(0.5)
    assert p50 is not None and 45 <= p50 <= 55


def test_clock_drift_alerts() -> None:
    m = ClockDriftMonitor(name="local", warn_ns=10, critical_ns=100)
    m.observe(0, 0)
    m.observe(20, 0)
    m.observe(0, 200)
    sev = [a.severity for a in m.alerts]
    assert "warn" in sev and "critical" in sev


def test_rolling_mean() -> None:
    m = ClockDriftMonitor(name="local")
    m.observe(10, 0)
    m.observe(20, 0)
    m.observe(30, 0)
    assert m.rolling_mean() == 20.0
