# AlgoTrading — Systematic Trading Program

**Operating document:** Build Plan v1.4-r1 + `docs/v1.4r1_errata_and_kickoff.md`
**Status:** Sprint 1 — framework only. No v0.2 strategy logic.

> Branch note: the operating document specifies `release/signoff-v1.4-r1`. The
> active development branch in this environment is
> `claude/release-signoff-v1.4-r1-RfVcm` per harness policy. Promote/tag to the
> spec-named branch before sign-off.

## What lives here

```
docs/                       Operating documents (errata, owners, procurement)
configs/                    YAML configuration (sessions, calendar, instruments)
data/                       (Empty — never commit market data)
src/algotrading/
  registry/                 Strategy registry (append-only)
  ingestion/                Tick + BBO ingestion skeleton
  calendar/                 Session calendar + holiday/half-day handling
  bars/                     5m / 60m bar builder
  fillmodel/                Fill model (limit, stop, collision)
  orders/                   Order state machine simulator
  baselines/                Random, drift-matched, reversed, session-exposure
  monitoring/               Latency + clock-drift scaffolding
  contamination/            Contamination log tooling + enforcement
tests/                      Unit tests, including bar boundary + fill collision
```

## Sprint 1 gate

Framework only. The following are **forbidden** in Sprint 1 (per errata §10):

- v0.2 signal logic
- B.7 / B.8 entry rules
- EMA / VWAP / ATR wired to v0.2
- strategy backtests, parameter tests
- validation / OOS / final-holdback queries
- visual chart inspection of v0.2 signals

CI enforces the freeze via `tests/test_sprint1_freeze.py`.

## Running tests

```
pip install -e .[dev]
pytest -q
```

Tests are pure Python + pytest. No external services required for unit tests.

## Owners

See `docs/OWNERS.md`. Risk reviewer must remain independent (v1.0 rule).

## Sign-off gates

See `docs/GATES.md` for the canonical state machine
(framework → v0.2 code → backtest → OOS → holdback → paper → live → scale-up).
