# AlgoTrading — Systematic Trading Program

**Operating document:** Build Plan v1.4-r1 + `docs/v1.4r1_errata_and_kickoff.md`
**Active CR:** `docs/change_requests/CR-001_v0.3_v0.4_registration_and_capital.md` (draft, awaiting countersign)

> Branch note: the operating document specifies `release/signoff-v1.4-r1`. The
> active development branch in this environment is
> `claude/release-signoff-v1.4-r1-RfVcm` per harness policy. Promote/tag to the
> spec-named branch before sign-off.

## What lives here

```
docs/                       Operating documents (errata, owners, procurement)
docs/appendices/            Pre-code spec appendices (B/C/D/E/H/I, B_v0.3, B_v0.4)
docs/change_requests/       Change Requests (CR-NNN)
configs/                    Sign-off matrix, risk limits, calendar, instruments
                            and the strategy registry (configs/strategy_registry.jsonl,
                            created on first append per CR-001)
data/                       (Empty — never commit market data)
src/algotrading/
  registry/                 Strategy registry (append-only JSONL)
  ingestion/                Tick + BBO ingestion skeleton
  calendar/                 Session calendar + holiday/half-day handling
  bars/                     5m / 60m bar builder
  fillmodel/                Fill model (limit, stop, collision)
  orders/                   Order state machine simulator
  baselines/                Random, drift-matched, reversed, session-exposure
  monitoring/               Latency + clock-drift scaffolding
  contamination/            Contamination log tooling + enforcement
  governance/               Phase-gate enforcement, sign-off matrix loader,
                            risk-limits guard
  strategy_v02/             v0.2 trend-pullback-continuation entry rules
  strategy_v03/             v0.3 mean-reversion-to-VWAP skeleton (CR-001;
                            entry/plan funcs gate-blocked behind `B_v0.3` row)
  strategy_v04/             v0.4 regime-classifier + switch-policy skeleton
                            (CR-001; switch-policy gate-blocked behind `B_v0.4` row)
tools/                      Operator scripts (e.g., `cr_001_apply.py`)
tests/                      Unit tests
```

## Status

The Sprint 1 framework-only freeze is **superseded** by the runtime
phase-gate system (see `tests/test_sprint1_freeze.py` for the marker). v0.2
strategy code lands under `src/algotrading/strategy_v02/` per the signed
pre-code rows (B/C/D/E/H). v0.3 / v0.4 are registered via CR-001 once that
CR is countersigned; their entry / switch-policy functions remain
gate-blocked behind unsigned rows (`B_v0.3`, `B_v0.4`).

The following remain forbidden in the current phase (gate-blocked, with
structured refusal messages):

- approved v0.2 backtest (broker rate sheet not signed)
- OOS query (validation freeze not signed)
- holdback (OOS not passed)
- paper trading (Appendix F + paper rows not signed)
- live trading at any size (paper not signed; multiple downstream rows)
- scale-up beyond 1 MES (Appendix G not signed)

See `docs/GATES.md` for the canonical state machine and
`configs/signoff_matrix.yml` for the current sign-off state.

## Running tests

```
pip install -e .[dev]
pytest -q
```

Tests are pure Python + pytest. No external services required for unit tests.

## Owners

See `docs/OWNERS.md`. Risk reviewer must remain independent (v1.0 rule).
