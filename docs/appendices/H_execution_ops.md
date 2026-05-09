# Appendix H — Execution & Ops Controls (sign-off template)

**Status:** Pre-code sign-off. Empty until signed; signed copies are committed
via PR.
**Frozen by:** errata §3 (pre-code sign-off rows are FROZEN).

---

## 1. Scope of this sign-off

This appendix locks the **execution and operational control surface** at
the specification level. Once signed, the following are binding inputs to
v0.2 strategy code and to any paper / live execution path, and may not be
edited without a Change Request:

- **Strategy-level lifecycle** (per family / version): see §1.a.
- **Order-level lifecycle** (per individual order): see §1.b.
- Kill-switch behaviour: triggers, ordering of cancel / flatten actions,
  and post-trip recovery preconditions.
- Reconnect / disconnect policy: what happens to working orders, OCO
  pairs, and stops on session loss; reconnect semantics and reconciliation.
- Position reconciliation: cadence, source of truth (broker vs internal),
  and resolution rule on mismatch.
- Daily loss-limit enforcement: detection, action, and lockout window
  (consumes the Director-set `daily_loss_limit_usd` from
  `configs/risk_limits.yml`).
- Latency and clock-drift alert thresholds (warn / critical), aligned with
  `LatencyMonitor` and `ClockDriftMonitor` defaults.

### 1.a Strategy-level lifecycle

The strategy lifecycle is the operational state of a strategy
*version* in the engine. It is distinct from, and outer to, the order
lifecycle below. One strategy can emit many orders; one strategy
transition (e.g., `STANDBY -> ACTIVE`) does not in itself produce an
order event.

States:

- `REGISTERED` — `StrategyRegistry` entry exists; engine has loaded
  rules; no engine attachment yet.
- `STANDBY` — engine attached, kill-switch armed, **not** emitting
  intents. This is the default in pre-market and after a kill-switch
  trip.
- `ACTIVE` — emitting intents subject to risk-limit caps; pre-conditions
  per `configs/signoff_matrix.yml` for the current gate satisfied.
- `PAUSED` — soft-tripwire hit (per §2.4 of `live_runbook_draft.md`);
  exits and stop adjustments allowed; no new entries.
- `ERROR_HALTED` — hard-tripwire or operator trip; orders cancelled and
  positions flattened per §H kill-switch sequence; no new orders until
  the post-incident review signs off.
- `RETIRED` — terminal: the strategy version is no longer eligible to
  emit intents. Successor versions register as new entries per §B.13.

Allowed transitions (other transitions raise an audit log entry and are
refused):

```
REGISTERED -> STANDBY
STANDBY    -> ACTIVE | RETIRED
ACTIVE     -> PAUSED | ERROR_HALTED | STANDBY
PAUSED     -> ACTIVE | STANDBY | ERROR_HALTED
ERROR_HALTED -> STANDBY     (only after post-incident review sign-off)
                  -> RETIRED      (review concludes the version is not
                                   eligible to resume)
```

Each transition is recorded in the contamination log
(`docs/research_contamination_log/README.md`) as `action_type=other`
with `dataset_used=live` or `dataset_used=paper` per the gate the
strategy is in. The transition row names the strategy version, the
prior state, the new state, and the trigger (operator id, monitor
alert id, or sign-off PR number).

### 1.b Order-level lifecycle

The order lifecycle is the state of a single order in the engine and
at the broker. It is implemented by
`src/algotrading/orders/state_machine.py`. States:

```
NEW -> PENDING_NEW -> WORKING -> [PARTIAL_FILL] -> FILLED
                              -> CANCELED
                              -> REJECTED
                              -> EXPIRED
```

Terminal set: `{FILLED, CANCELED, REJECTED, EXPIRED}`. No transition
out of a terminal state. Partial-fill accounting per
`OrderStateMachine.fill`: rejects qty <= 0, rejects qty > remaining,
advances `qty_filled`, transitions to `FILLED` only when
`qty_filled == qty_total`.

### 1.c Lifecycle separation rule

The two lifecycles are independent:

- A strategy in `STANDBY` may have working orders to which it is no
  longer reacting; those orders complete or cancel under the order
  lifecycle. The strategy does **not** transition back to `ACTIVE`
  because of an order event.
- A strategy in `ACTIVE` may have zero working orders at any moment;
  this is normal, not a state change.
- A strategy `ERROR_HALTED` immediately drives all of its working
  orders to `CANCELED` (cancel-all then flatten); the order
  transitions are recorded in the order lifecycle, the strategy
  transition is recorded separately.
- The contamination log records both: the strategy transition (one
  row) and any non-trivial order transitions resulting from it.

This appendix sits alongside Appendix F (broker integration / OCO
finalization). H is the internal control surface; F is the broker-facing
contract. F is signed at the paper-trading gate (errata §3); H is signed
now as a pre-code row.

## 2. What this sign-off unblocks

Per `docs/GATES.md`:

- The `v0.2 strategy code` gate (jointly with B, C, D, E). v0.2 logic may
  be wired against the order state machine and monitoring scaffolding
  once this row is signed.

This sign-off does **not** unblock paper or live trading. Those gates
require Appendix F finalization for the chosen broker plus Appendix I
counsel sign-off (per `docs/GATES.md`; errata §4).

## 3. Dependencies on other appendices

- **Appendix B**: forced-flatten timing in B must be expressible by the
  state machine in H. Reviewer confirms B's forced-flatten is a
  `cancel` followed by a market order, not a separate state.
- **Appendix D**: fills produced by `FillModel` drive `OrderEvent.FILL`
  and `OrderEvent.PARTIAL_FILL` here. Bracket worst-case stop fills
  (Appendix D §5 item 4) must be expressible as a single `FILL` event
  with the worst-case price.
- **Appendix E**: realised drawdown used by E's gates depends on H's
  forced-flatten and kill-switch behaviour. Loosening H here would
  invalidate previously signed E thresholds.
- **`configs/risk_limits.yml`**: `daily_loss_limit_usd`,
  `max_acceptable_losing_streak`, `aggregate_program_drawdown_limit_pct`,
  and `risk_of_ruin_threshold_pct` are consumed here. They are signed
  in the risk-limits file by the Director Sponsor, not redefined here.

## 4. Source modules and tests referenced

- `src/algotrading/orders/state_machine.py` —
  - `OrderState`: `NEW`, `PENDING_NEW`, `WORKING`, `PARTIAL_FILL`,
    `FILLED`, `CANCELED`, `REJECTED`, `EXPIRED`.
  - `OrderEvent`: `SUBMIT`, `ACK`, `REJECT`, `PARTIAL_FILL`, `FILL`,
    `CANCEL`, `EXPIRE`.
  - `_ALLOWED` transition table; `_TERMINAL` set.
  - `OrderStateMachine.fill` partial / full handling.
  - `OrderStateError` raised on invalid transition.
- `src/algotrading/monitoring/latency.py` —
  - `LatencyMonitor` (warn 50ms, critical 250ms by default; rolling
    p50 / p95 / p99 via `percentile`).
  - `ClockDriftMonitor` (warn 10ms, critical 250ms by default; rolling
    mean). The critical threshold is aligned with the spec halt-new-
    entries rule; stricter operational thresholds require Director /
    Risk approval recorded in `configs/risk_limits.yml` notes.
  - `MonitorAlert` severities: `info` | `warn` | `critical`.
- `src/algotrading/fillmodel/model.py` — produces fills consumed here.
- `tests/test_orders.py`, `tests/test_monitoring.py`,
  `tests/test_fillmodel.py`.

## 5. Review checklist

The signer must verify each item below by direct inspection. Initial each
box. Unchecked items block the signature.

1. [ ] The state set in code matches the spec exactly: `NEW`,
       `PENDING_NEW`, `WORKING`, `PARTIAL_FILL`, `FILLED`, `CANCELED`,
       `REJECTED`, `EXPIRED`. No additional or omitted states.
2. [ ] The terminal set is `{FILLED, CANCELED, REJECTED, EXPIRED}` and
       no transition out of a terminal state is permitted. The reviewer
       has confirmed `_transition` raises `OrderStateError` on terminal
       inputs.
3. [ ] The transition table `_ALLOWED` is reviewed end-to-end:
       (a) `NEW` -> `{PENDING_NEW, REJECTED}` only;
       (b) `PENDING_NEW` -> `{WORKING, REJECTED}` only;
       (c) `WORKING` and `PARTIAL_FILL` -> `{PARTIAL_FILL, FILLED,
       CANCELED, EXPIRED}`. No transition from `WORKING` directly back
       to `PENDING_NEW`.
4. [ ] Partial-fill accounting is correct: `OrderStateMachine.fill`
       rejects qty <= 0, rejects qty > remaining, advances
       `qty_filled`, and transitions to `FILLED` only when
       `qty_filled == qty_total`.
5. [ ] Kill-switch behaviour is specified to a single action sequence:
       (a) cancel all working orders, (b) flatten any open position
       with a market order, (c) refuse new submissions until a manual
       reset. The reviewer has confirmed there is no path that flattens
       before cancelling (which would race a working entry).
6. [ ] Kill-switch triggers are enumerated: daily loss limit hit,
       losing-streak threshold hit, drawdown ceiling breach,
       clock-drift critical alert, latency critical alert sustained
       for N samples, manual operator trip. Each trigger names the
       Director-set value or monitor it consumes.
7. [ ] Reconnect / disconnect policy is written down: on TCP / session
       loss, working orders are presumed alive at the broker until
       confirmed otherwise on reconnect; OCO residence (server vs
       platform-local) is named explicitly per the broker's written
       reply (`docs/PROCUREMENT.md` row "OCO residence confirm").
8. [ ] Reconnect reconciliation rule: broker open-orders snapshot is
       the source of truth on reconnect; any internal-only working
       order that does not match a broker order is canceled
       internally and logged. Any broker-only order that does not
       match an internal record is flattened and logged as an
       anomaly.
9. [ ] Position reconciliation cadence is named (per-tick during RTH
       is acceptable; otherwise an explicit interval). The reviewer
       has confirmed the cadence applies to **every** session,
       including overnight (`SessionType.OVERNIGHT`).
10. [ ] Daily loss-limit enforcement consumes `daily_loss_limit_usd`
        from `configs/risk_limits.yml` (`locked: true`). The reviewer
        has confirmed there is no hard-coded fallback if the value is
        missing — the system refuses to start.
11. [ ] Latency alert thresholds in code (`LatencyMonitor.warn_ns =
        50ms`, `critical_ns = 250ms`) match the values written in this
        appendix, or this appendix explicitly overrides them with
        documented justification. Same check for `ClockDriftMonitor`
        (`warn_ns = 10ms`, `critical_ns = 250ms` — spec halt threshold).
        Stricter operational thresholds require Director / Risk approval
        recorded in `configs/risk_limits.yml` notes.
12. [ ] Negative latency (`local_ns < exchange_ns`) is treated as
        `critical` (clock skew or feed corruption). The reviewer has
        confirmed the branch in `LatencyMonitor.observe`.
13. [ ] Monitor alert storage is bounded by `window`; the reviewer has
        confirmed there is no unbounded list growth path under sustained
        alerting (alerts list is documented as bounded by retention
        policy at the metrics-sink seam, not in-process — flag if
        in-process unboundedness is a concern for paper / live).
14. [ ] No v0.2 strategy logic is present anywhere under
        `src/algotrading/` at the time of signing (Sprint 1 freeze;
        errata §3, §9). The reviewer has searched for any module named
        after a B.7 / B.8 rule and found none.
15. [ ] Independence: the Engineering signer for this appendix is not
        the Risk Reviewer (per `docs/OWNERS.md`).

## 6. Sign-off block

Empty by default. To sign, fill the row, commit on a branch, and open a PR
labelled `signoff-appendix-h`. Per `configs/signoff_matrix.yml`, the
required `signer_role` is **Engineering**. The Risk Reviewer must
independently acknowledge the PR (independence rule, `docs/OWNERS.md`).

| Field           | Value |
| --------------- | ----- |
| Signer name     |       |
| Role            |       |
| Date (ISO-8601) |       |
| Notes           |       |

Allowed roles for this appendix (per `docs/OWNERS.md` and
`configs/signoff_matrix.yml`):

- Engineering — data + engine (primary).
- Ops — broker / OCO confirmation (ack on §5 items 7 - 8; signs Appendix
  F separately at the paper gate).
- Risk reviewer (independence ack on the PR; not a co-signer).
