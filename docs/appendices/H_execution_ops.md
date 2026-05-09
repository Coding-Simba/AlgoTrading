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

- **Strategy-version lifecycle** (per family / version, operational): §1.a.
- **Execution lifecycle** (per single trade attempt): §1.b.
- **Order-level lifecycle** (per individual broker order): §1.c.
- **Lifecycle mapping** (which order states are allowed in each execution
  state, and which execution states an active strategy version may be in):
  §1.d.
- **Protected flatten sequence**: §1.e. The default flatten keeps the
  protective stop ACTIVE until the broker confirms flat. Cancel-first is
  rejected unless the broker has a documented broker-native atomic
  flatten path.
- Kill-switch behaviour: the kill switch invokes the §1.e protected
  flatten sequence (it does **not** define a separate cancel-first
  path). Triggers, the §1.e sequence, and post-trip recovery
  preconditions are governed exclusively by §1.e.
- Reconnect / disconnect policy.
- Position reconciliation.
- Daily loss-limit enforcement (consumes the Director-set
  `daily_loss_limit_usd` from `configs/risk_limits.yml`).
- Latency and clock-drift alert thresholds, aligned with `LatencyMonitor`
  and `ClockDriftMonitor` defaults.

### 1.a Strategy-version lifecycle

Operational state of a strategy *version* in the engine. Outer to the
execution lifecycle. One strategy version can run many executions over its
lifetime; one strategy-version transition (e.g., `STANDBY -> ACTIVE`) does
not in itself produce an order event.

States:

- `REGISTERED` — `StrategyRegistry` entry exists; engine has loaded
  rules; no engine attachment yet.
- `STANDBY` — engine attached, kill-switch armed, **not** emitting
  intents. Default in pre-market and after a kill-switch trip.
- `ACTIVE` — emitting intents subject to risk-limit caps; pre-conditions
  per `configs/signoff_matrix.yml` for the current gate satisfied.
- `PAUSED` — soft-tripwire hit (per §2.4 of `live_runbook_draft.md`);
  exits and stop adjustments allowed; no new entries.
- `ERROR_HALTED` — hard-tripwire or operator trip; protected-flatten
  invoked per §1.e; no new orders until post-incident review signs off.
- `RETIRED` — terminal: the strategy version is no longer eligible to
  emit intents. Successor versions register as new entries per §B.13.

Allowed transitions:

```
REGISTERED   -> STANDBY
STANDBY      -> ACTIVE | RETIRED
ACTIVE       -> PAUSED | ERROR_HALTED | STANDBY
PAUSED       -> ACTIVE | STANDBY | ERROR_HALTED
ERROR_HALTED -> STANDBY (only after post-incident review sign-off)
              -> RETIRED (review concludes the version is not eligible
                          to resume)
```

Each transition is recorded in the contamination log
(`docs/research_contamination_log/README.md`) as `action_type=other` with
`dataset_used=live` or `dataset_used=paper` per the gate the strategy is
in. The transition row names the strategy version, the prior state, the
new state, and the trigger (operator id, monitor alert id, or sign-off PR
number).

### 1.b Execution lifecycle

State of a *single trade attempt*. Inner to the strategy-version
lifecycle. The execution lifecycle is reset to `FLAT` between trades; a
single strategy version may go through this lifecycle many times in a
session. Implemented in `src/algotrading/orders/execution_lifecycle.py`.

States:

- `FLAT` — no open position, no working orders. New entries are only
  permitted from this state.
- `SIGNAL_PENDING` — a signal has been generated; no broker order yet.
- `ENTRY_SENT` — entry order in `NEW` / `PENDING_NEW` / `WORKING` at the
  broker.
- `ENTRY_FILLED` — entry order `FILLED`; bracket (stop + target) not yet
  acknowledged by the broker.
- `BRACKET_PENDING` — bracket children submitted; in `NEW` /
  `PENDING_NEW` / `WORKING`.
- `POSITION_PROTECTED` — bracket `WORKING`; broker confirms OCO /
  bracket relationship is active.
- `EXIT_PENDING` — stop fill, target fill, clock flatten, or pre-news
  flatten in progress.
- `FLAT_RECONCILING` — broker position should be 0; reconcile broker
  vs internal state per §1.e.
- `ERROR_HALTED` — manual review required; no new entries.

Allowed transitions:

```
FLAT               -> SIGNAL_PENDING
SIGNAL_PENDING     -> ENTRY_SENT | FLAT
ENTRY_SENT         -> ENTRY_FILLED | FLAT
ENTRY_FILLED       -> BRACKET_PENDING
BRACKET_PENDING    -> POSITION_PROTECTED | EXIT_PENDING
POSITION_PROTECTED -> EXIT_PENDING
EXIT_PENDING       -> FLAT_RECONCILING
FLAT_RECONCILING   -> FLAT
```

ERROR_HALTED is reachable from any non-terminal state via an explicit
transition with a non-empty reason. Exit from ERROR_HALTED is only to
FLAT, and only with a `reason` containing `manual_review` recorded in
the lifecycle history.

Bracket failure modes that drive ERROR_HALTED:

- Bracket rejection by the broker (any leg).
- Bracket-ack timeout (configurable per broker; default 5 seconds).
- Broker / internal mismatch on the bracketed position.
- Position flip (net qty crosses zero unexpectedly).

### 1.c Order-level lifecycle

State of a single broker order. Implemented in
`src/algotrading/orders/state_machine.py`. States:

```
NEW -> PENDING_NEW -> WORKING -> [PARTIAL_FILL] -> FILLED
                              -> CANCELED
                              -> REJECTED
                              -> EXPIRED
```

Terminal set: `{FILLED, CANCELED, REJECTED, EXPIRED}`. No transition out
of a terminal state. Partial-fill accounting per
`OrderStateMachine.fill`: rejects qty <= 0, rejects qty > remaining,
advances `qty_filled`, transitions to `FILLED` only when
`qty_filled == qty_total`.

### 1.d Lifecycle mapping

The three lifecycles run side-by-side. The mapping below specifies which
order states are permitted in each execution state, and which execution
state an active strategy version may be in at any given moment. A
runtime check that violates this mapping triggers ERROR_HALTED on the
execution lifecycle.

**Execution state → allowed order states:**

| Execution state    | Allowed order states                                             |
| ------------------ | ---------------------------------------------------------------- |
| FLAT               | no open position; no working orders                              |
| SIGNAL_PENDING     | no broker order yet                                              |
| ENTRY_SENT         | entry: `NEW` / `PENDING_NEW` / `WORKING`                         |
| ENTRY_FILLED       | entry: `FILLED`; bracket children not yet acknowledged           |
| BRACKET_PENDING    | stop + target: `NEW` / `PENDING_NEW` / `WORKING`                 |
| POSITION_PROTECTED | stop + target: `WORKING`; broker confirms OCO / bracket active   |
| EXIT_PENDING       | exit fill or flatten in progress (see §1.e for the sequence)     |
| FLAT_RECONCILING   | broker position should be 0; no working orders should remain     |
| ERROR_HALTED       | manual review required; no new entries; existing orders frozen until manual reset |

**Strategy-version state → allowed execution states:**

| Strategy-version state | Allowed execution states                              |
| ---------------------- | ----------------------------------------------------- |
| REGISTERED             | (none — engine not attached yet)                      |
| STANDBY                | `FLAT` only (no new signals)                          |
| ACTIVE                 | any execution state (signals permitted)               |
| PAUSED                 | `FLAT` / `EXIT_PENDING` / `FLAT_RECONCILING` only — exits and stop adjustments only |
| ERROR_HALTED (strategy)| `EXIT_PENDING` / `FLAT_RECONCILING` / `ERROR_HALTED` (execution) |
| RETIRED                | `FLAT` only (terminal)                                |

A strategy-version in `STANDBY` may still have execution lifecycles in
non-FLAT states from prior signals; those resolve through the execution
lifecycle on their own (target / stop / flatten paths). The
strategy-version does **not** transition back to `ACTIVE` because of an
order or execution event.

### 1.e Protected flatten sequence

Implemented in `src/algotrading/orders/flatten.py`.

**Default sequence** (the only sanctioned sequence unless §1.e atomic
override applies):

1. `HALT_NEW_ENTRIES` — strategy-version moves to `STANDBY` or
   `ERROR_HALTED`; the execution lifecycle continues for the in-flight
   trade.
2. `KEEP_STOP_ACTIVE` — the protective stop **stays working at the
   broker**. Do not cancel it.
3. `SUBMIT_MARKET_FLATTEN` — submit a market order to flatten the held
   position.
4. `CONFIRM_BROKER_FLAT` — read the broker open-orders / position
   snapshot; the position must be 0 and the working order count must be
   0 except for the still-active protective stop.
5. `CANCEL_REMAINING_OCO` — only after step 4: cancel the now-redundant
   protective stop / OCO sibling.

**Mismatch / flip behaviour.** At any point in the sequence, if (a) the
broker reports a position whose sign differs from the internal record,
(b) the position size flips through zero unexpectedly, or (c) the
broker open-orders snapshot diverges from the local order log beyond
the CONFIRM_BROKER_FLAT check, drive the execution lifecycle to
`ERROR_HALTED` immediately. The protective stop remains working.
Resolution is via post-incident review; no automatic recovery.

**Kill-switch uses §1.e protected flatten.** The kill switch is not a
separate cancel-first path. When tripped (clock flatten, pre-news
flatten, or any tripwire / mismatch / flip listed under "Mismatch /
flip behaviour"), it invokes the default sequence above — `HALT_NEW_ENTRIES`
→ `KEEP_STOP_ACTIVE` → `SUBMIT_MARKET_FLATTEN` → `CONFIRM_BROKER_FLAT`
→ `CANCEL_REMAINING_OCO` — and on any mismatch or position flip,
transitions the execution lifecycle to `ERROR_HALTED`. There is no
default cancel-first sequence.

**Atomic override.** Cancel-first (or any sequence that cancels the
protective stop before the broker confirms flat) is permitted **only**
when the chosen broker offers a documented broker-native atomic flatten
that guarantees protection during the call. The atomic override:

- requires `atomic_flatten=True` AND `broker_atomic_flatten_documented=True`
  in the call site (see
  `src/algotrading/orders/flatten.py:protected_flatten_plan`);
- requires the broker's written confirmation on file at
  `docs/PROCUREMENT.md` row "OCO residence confirm" to describe the
  atomic flatten path (atomic call name, idempotency, partial-fill
  behaviour, failure modes);
- replaces steps 2–5 above with a single `ATOMIC_FLATTEN` step followed
  by `CONFIRM_BROKER_FLAT`.

The validator in `flatten.py:validate_flatten_plan` rejects:

- any default plan that places `CANCEL_REMAINING_OCO` before
  `CONFIRM_BROKER_FLAT`;
- any default plan missing `KEEP_STOP_ACTIVE` between
  `HALT_NEW_ENTRIES` and `SUBMIT_MARKET_FLATTEN`;
- any atomic plan that includes `CANCEL_REMAINING_OCO` (the broker-native
  call owns the cancel) or a manual `SUBMIT_MARKET_FLATTEN` (atomic
  replaces the manual flatten);
- any atomic plan missing `ATOMIC_FLATTEN`.

This appendix sits alongside Appendix F (broker integration / OCO
finalization). H is the internal control surface; F is the broker-facing
contract. F is signed at the paper-trading gate (errata §3); H is signed
now as a pre-code row.

## 2. What this sign-off unblocks

Per `docs/GATES.md`:

- The `v0.2 strategy code` gate (jointly with B, C, D, E). v0.2 logic may
  be wired against the order state machine, the execution lifecycle, and
  the monitoring scaffolding once this row is signed.

This sign-off does **not** unblock paper or live trading. Those gates
require Appendix F finalization for the chosen broker (per
`docs/GATES.md`). Appendix I is a scope-control note for the current
internal-only scope (see `docs/appendices/I_legal_scope_note.md`); it
does not gate paper or internal live trading. Counsel review is required
only on a scope-expansion trigger.

## 3. Dependencies on other appendices

- **Appendix B**: forced-flatten timing in B (clock flatten, pre-news
  flatten) is implemented by §1.e protected flatten.
- **Appendix D**: fills produced by `FillModel` drive `OrderEvent.FILL`
  and `OrderEvent.PARTIAL_FILL` here. Bracket worst-case stop fills must
  be expressible as a single `FILL` event with the worst-case price, and
  must drive the execution lifecycle directly to `EXIT_PENDING`.
- **Appendix E**: realised drawdown used by E's gates depends on H's
  protected flatten and kill-switch behaviour. Loosening §1.e or the
  ERROR_HALTED rules here would invalidate previously signed E thresholds.
- **`configs/risk_limits.yml`**: `daily_loss_limit_usd`,
  `max_acceptable_losing_streak`, `aggregate_program_drawdown_limit_pct`,
  and `risk_of_ruin_threshold_pct` are consumed here.

## 4. Source modules and tests referenced

- `src/algotrading/orders/state_machine.py` — order-level lifecycle
  (`OrderState`, `OrderEvent`, `_ALLOWED`, `_TERMINAL`,
  `OrderStateMachine`, `OrderStateError`).
- `src/algotrading/orders/execution_lifecycle.py` — execution lifecycle
  (`ExecutionState`, `ExecutionLifecycle`, `ExecutionStateError`).
- `src/algotrading/orders/flatten.py` — protected flatten sequencing
  (`FlattenStep`, `DEFAULT_FLATTEN_SEQUENCE`, `ATOMIC_FLATTEN_SEQUENCE`,
  `protected_flatten_plan`, `validate_flatten_plan`,
  `FlattenSequenceError`).
- `src/algotrading/monitoring/latency.py` — `LatencyMonitor` (warn 50ms,
  critical 250ms by default); `ClockDriftMonitor` (warn 10ms, critical
  250ms by default — spec halt threshold).
- `src/algotrading/fillmodel/model.py` — produces fills consumed here.
- `tests/test_orders.py`, `tests/test_execution_lifecycle.py`,
  `tests/test_flatten.py`, `tests/test_monitoring.py`,
  `tests/test_fillmodel.py`.

## 4.x Required sign-off checks (summary)

Appendix H may not be signed unless **all** of the following hold:

- [ ] Strategy-version lifecycle is defined (§1.a).
- [ ] Execution lifecycle is defined (§1.b).
- [ ] Order-level lifecycle is defined (§1.c).
- [ ] Lifecycle mapping table is present (§1.d).
- [ ] Protected-flatten sequence keeps the protective stop active until
      flat confirmation (§1.e).
- [ ] Cancel-first is allowed only for documented broker-native atomic
      flatten (§1.e atomic override).
- [ ] `ERROR_HALTED` requires manual review before restart, on both the
      strategy-version and the execution lifecycle.

## 5. Review checklist

The signer must verify each item below by direct inspection. Initial each
box. Unchecked items block the signature.

1. [ ] The order-level state set in code matches §1.c exactly:
       `NEW`, `PENDING_NEW`, `WORKING`, `PARTIAL_FILL`, `FILLED`,
       `CANCELED`, `REJECTED`, `EXPIRED`. Terminal set
       `{FILLED, CANCELED, REJECTED, EXPIRED}` is exhaustive and no
       transition out of a terminal is permitted.
2. [ ] The execution-lifecycle state set in code matches §1.b exactly:
       `FLAT`, `SIGNAL_PENDING`, `ENTRY_SENT`, `ENTRY_FILLED`,
       `BRACKET_PENDING`, `POSITION_PROTECTED`, `EXIT_PENDING`,
       `FLAT_RECONCILING`, `ERROR_HALTED`. New entries are accepted
       only from `FLAT`. The reviewer has confirmed the test
       `tests/test_execution_lifecycle.py:test_no_new_entry_outside_flat`.
3. [ ] Bracket rejection and bracket-ack timeout drive the execution
       lifecycle to `ERROR_HALTED` (cite
       `tests/test_execution_lifecycle.py:test_bracket_rejection_drives_error_halted`,
       `:test_bracket_ack_timeout_drives_error_halted`).
4. [ ] Exit from execution `ERROR_HALTED` requires a `reason`
       containing `manual_review` (cite
       `tests/test_execution_lifecycle.py:test_error_halted_cannot_exit_without_manual_review`).
5. [ ] The strategy-version state set matches §1.a; allowed transitions
       table reviewed; ERROR_HALTED → STANDBY only after post-incident
       review sign-off.
6. [ ] §1.d mapping table is enforced: a runtime check that observes a
       broker order in a state not allowed for the current execution
       state drives ERROR_HALTED on the execution lifecycle and pages
       per §6 of `docs/ops/live_runbook_draft.md`.
7. [ ] §1.e protected flatten is the default. The reviewer has
       confirmed there is **no** default sequence in code, runbook, or
       ops docs that cancels the protective stop before the broker
       confirms flat.
8. [ ] §1.e atomic override is gated on
       `broker_atomic_flatten_documented=True` and on the broker
       confirmation file at `docs/PROCUREMENT.md` describing the
       broker-native atomic flatten path. Both must be present
       simultaneously; either alone is rejected (cite
       `tests/test_flatten.py:test_atomic_flatten_requires_documented_broker_path`).
9. [ ] Position-reconciliation cadence is named (per-tick during RTH is
       acceptable; otherwise an explicit interval) and applies to
       overnight (`SessionType.OVERNIGHT`) sessions as well.
10. [ ] Kill-switch triggers are enumerated and each names the
        Director-set value or monitor it consumes: daily loss limit,
        losing-streak threshold, drawdown ceiling, clock-drift
        critical, latency critical sustained for N samples, manual
        operator trip, §1.d mapping violation.
11. [ ] Daily loss-limit enforcement consumes `daily_loss_limit_usd`
        from `configs/risk_limits.yml` (`locked: true`). No
        hard-coded fallback.
12. [ ] Latency thresholds match (`LatencyMonitor.warn_ns = 50ms`,
        `critical_ns = 250ms`). Clock-drift thresholds match
        (`ClockDriftMonitor.warn_ns = 10ms`,
        `critical_ns = 250ms` — spec halt threshold). Stricter
        operational thresholds require Director / Risk approval recorded
        in `configs/risk_limits.yml` notes.
13. [ ] Negative latency (`local_ns < exchange_ns`) is treated as
        `critical`.
14. [ ] No v0.2 strategy logic is present anywhere under
        `src/algotrading/` at the time of signing (Sprint 1 freeze;
        errata §3, §9).
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
- Ops — broker / OCO confirmation (ack on §1.e atomic override path; signs
  Appendix F separately at the paper gate).
- Risk reviewer (independence ack on the PR; not a co-signer).
