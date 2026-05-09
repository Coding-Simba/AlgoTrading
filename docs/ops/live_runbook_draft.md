# Live Runbook — DRAFT

> **DRAFT — broker placeholder. Paper trading is BLOCKED until this is broker-specific and signed (Appendix F).**

**Status:** DRAFT. Not broker-specific. Not production-ready. Not approved for any
form of live or paper trading.
**Owner:** Ops (TBD-OPS — see `docs/OWNERS.md`)
**Applies to:** v1.4-r1, framework only.
**Issued:** 2026-05-09.

---

## 0. Purpose and scope

This document is the live-trading operations runbook. It is written against a
**broker placeholder**. Every step that depends on broker-specific behaviour
(order routing, OCO residence, disconnect handling, error code mapping,
reconciliation file format, etc.) is marked TBD-BROKER. None of those steps may
be relied on until:

1. A broker has been selected.
2. The vendor confirmation responses requested in `docs/procurement/` are on
   file (`docs/vendor-replies/<vendor>-*.md`).
3. The procurement answers and runbook adjustments are captured in
   `docs/ops/broker_specific_questions.md` and reviewed.
4. Appendix F is finalized for that broker.

Appendix I is a scope-control note for this internal-only project (see
`docs/appendices/I_legal_scope_note.md`); it does **not** gate paper or
internal live trading. Counsel review is required only on a scope-expansion
trigger (client / outside / pooled capital, paid signals, paid advice,
copy-trading, public performance marketing, managed accounts).

Until items 1–4 above are complete, **paper trading is BLOCKED** per
`docs/GATES.md`. Live trading is BLOCKED additionally on the paper gate per
§E.3 and on Appendix G for any size beyond the small-size minimum.

This runbook is draft only and does not authorize paper / live trading
until broker-specific procedures are filled in.

---

## 1. Startup checklist (pre-market)

Run in order. A failed step halts startup. Do not proceed with any item marked
TBD-BROKER until the broker is selected and the answer is on file.

### 1.1 System checks

- [ ] Host OS healthy: disk free > 20 percent, memory free > 25 percent, no
      pending kernel update requiring reboot.
- [ ] Process supervisor reports all framework services in `READY` state.
- [ ] Log rotation has run; previous session's logs archived under
      `logs/archive/<date>/`.
- [ ] Configuration on disk matches the committed config: `git status` clean
      on `configs/`.
- [ ] Strategy registry hash matches the build's expected hash (see
      `src/algotrading/registry/registry.py`).

### 1.2 Time-sync verification

- [ ] NTP / chrony reports `synchronised: yes` with a stratum source.
- [ ] `ClockDriftMonitor` (in `src/algotrading/monitoring/latency.py`) is
      armed against the broker session timestamp once it connects. Defaults
      from that module: `warn_ns = 10_000_000` (10 ms),
      `critical_ns = 250_000_000` (250 ms — spec halt threshold). Any
      `critical` alert before market open aborts startup.
- [ ] Local UTC offset confirmed within 1 ms of `time.google.com`.

### 1.3 Market data session

- [ ] Primary market-data session connected, heartbeating, and serving
      live ticks for the watchlist.
- [ ] Secondary (cross-check) data vendor session connected if procured.
- [ ] First-tick latency observed under `LatencyMonitor` defaults
      (`warn_ns = 50_000_000` = 50 ms; `critical_ns = 250_000_000` = 250 ms).
      A `critical` alert during warm-up aborts startup.
- [ ] Bar builder (`src/algotrading/bars/`) is producing 5m and 60m bars and
      boundary tests pass for the current session.

### 1.4 Broker session

- [ ] Broker session connected and authenticated.
- [ ] Account number matches the configured trading account.
- [ ] Working order book pulled from broker; reconciled against local order
      log (none expected at startup; any divergence halts startup).
- [ ] Position book pulled from broker; reconciled against local position
      state (see `docs/ops/reconciliation_checklist.md`).
- [ ] TBD-BROKER: confirm OCO residence (server / exchange / platform-local)
      matches the answer on file.
- [ ] TBD-BROKER: confirm disconnect / reconnect semantics for working orders
      and OCO pairs match the answer on file.

### 1.5 Safety surfaces

- [ ] Kill-switch armed and tested via a dry-run of the §1.e
      protected-flatten plan (`HALT_NEW_ENTRIES` →
      `KEEP_STOP_ACTIVE` → `SUBMIT_MARKET_FLATTEN` →
      `CONFIRM_BROKER_FLAT` → `CANCEL_REMAINING_OCO`) returns success
      without submitting any orders. There is no default cancel-first
      path.
- [ ] Position state reconciled with broker (see §1.4).
- [ ] Contamination log reachable and writable; latest entry timestamp visible
      (see `src/algotrading/contamination/log.py`).
- [ ] Partition lock present (`configs/data_partitions.yml` committed,
      Appendix C / §C.9).
- [ ] Risk limits loaded and locked (see
      `src/algotrading/governance/risk_limits.py`).
- [ ] Sign-off matrix present and current; all required signers for the
      current gate have signed (see `src/algotrading/governance/signoff.py`
      and `docs/signoff/`).

### 1.6 Final gate

- [ ] All of §1.1–§1.5 PASS.
- [ ] Ops on-call confirms readiness in the chat channel and in the daily ops
      log.
- [ ] Risk reviewer has not raised a hold.

If any item fails, the system stays in pre-market `STANDBY`. **Do not bypass.**

---

## 2. In-session monitoring

### 2.1 What is monitored

- Latency of each tick (exchange-stamped vs. local-receive) via
  `LatencyMonitor`.
- Clock drift via `ClockDriftMonitor`.
- Order state machine transitions (`src/algotrading/orders/state_machine.py`).
- Working order count vs. broker working order count (continuous).
- Position size vs. broker position size (continuous).
- Realised + unrealised P&L vs. daily loss tripwire.
- Strategy-emitted intents vs. risk-limit caps.
- Contamination-log writes (any entry during trading is a hold-flag, not a
  stop, but is reviewed by Risk).

### 2.2 LatencyMonitor thresholds

Defaults from `src/algotrading/monitoring/latency.py`:

| Monitor              | warn               | critical            |
| -------------------- | ------------------ | ------------------- |
| `LatencyMonitor`     | 50 ms (50_000_000 ns)  | 250 ms (250_000_000 ns) |
| `ClockDriftMonitor`  | 10 ms (10_000_000 ns)  | 250 ms (250_000_000 ns) |

A `warn` increments a counter and posts to the ops channel. A `critical`
pages the on-call (see §6) and arms the kill-switch path. Any negative
latency observation is logged at `critical` regardless of magnitude (sign of
clock-skew or tick-replay bug).

### 2.3 Order state machine

Reference: `src/algotrading/orders/state_machine.py`. Allowed transitions:

```
NEW -> PENDING_NEW -> WORKING -> [PARTIAL_FILL] -> FILLED
                              -> CANCELED
                              -> REJECTED
                              -> EXPIRED
```

Any `OrderStateError` in session is treated as a `critical` alert.

### 2.4 Daily loss tripwires

Tripwire values are owned by the Director Sponsor (see `docs/OWNERS.md`) and
must be loaded from `configs/risk_limits.yml` at startup. Tripwire actions:

- `warn`: post to ops, no trading change.
- `soft`: stop new entries; allow exits and stop adjustments.
- `hard`: trigger ERROR_HALTED (see §4).

Specific dollar values are TBD — placeholder pending Director Sponsor sign-off.

---

## 3. Manual flatten (protected flatten)

For manual flatten, pre-news flatten, or session-end flatten, use the
protected-flatten sequence specified in Appendix H §1.e and implemented
in `src/algotrading/orders/flatten.py`. **Cancel-first is forbidden**
unless the chosen broker offers a documented broker-native atomic
flatten (see §3.4 atomic override).

### 3.1 Default protected sequence

Run in order. The protective stop **stays working at the broker** until
step 4 confirms the broker is flat.

1. **Halt new entries.** Move the strategy-version to `STANDBY` (or
   `ERROR_HALTED` if invoked by a hard tripwire); refuse new strategy
   intents. The execution lifecycle continues to drive the in-flight
   trade through to FLAT.
2. **Keep protective stop active.** Do **not** cancel the protective
   stop. It stays working at the broker for the duration of steps 3–4.
3. **Submit market flatten order** (or documented broker-native atomic
   flatten under §3.4).
4. **Confirm broker position is flat.** Read the broker open-orders /
   position snapshot. The position must be 0 and the working order
   count must be 0 except for the still-active protective stop.
5. **Cancel remaining OCO leg.** Only after step 4: cancel the
   now-redundant protective stop / OCO sibling.
6. **Verify broker position equals internal position.** Reconcile the
   local order log against the broker open-orders snapshot.
7. **If mismatch or position flip occurs, transition to `ERROR_HALTED`.**
   The protective stop remains working pending Risk-Reviewer disposition.

### 3.2 Mismatch / flip behaviour

At any point in the sequence, if (a) the broker reports a position
whose sign differs from the internal record, (b) the position size
flips through zero unexpectedly, or (c) the broker open-orders snapshot
diverges from the local order log beyond the CONFIRM_BROKER_FLAT check,
drive the execution lifecycle to `ERROR_HALTED` immediately. The
protective stop remains working. Resolution is via post-incident
review; no automatic recovery.

### 3.3 Idempotency

The flatten command is idempotent: re-running it on an already-flat
account issues no new orders and returns success. If two attempts
report divergence, escalate to ERROR_HALTED (§4).

### 3.4 Atomic override (broker-native only)

A cancel-first or single-call atomic flatten is permitted only when the
chosen broker offers a documented broker-native atomic flatten that
guarantees protection during the call. The atomic override:

- requires `atomic_flatten=True` AND
  `broker_atomic_flatten_documented=True` in the call site (see
  `src/algotrading/orders/flatten.py:protected_flatten_plan`);
- requires the broker's written confirmation on file at
  `docs/PROCUREMENT.md` row "OCO residence confirm" describing the
  atomic flatten path (atomic call name, idempotency, partial-fill
  behaviour, failure modes);
- replaces steps 2–5 above with a single `ATOMIC_FLATTEN` step
  followed by `CONFIRM_BROKER_FLAT`.

### 3.5 Confirm

Manual flatten is "confirmed" only when:

- Broker working orders = 0 (after step 5 / atomic CONFIRM_BROKER_FLAT).
- Broker positions = 0.
- Local order log shows every previously-working order in a terminal state.
- Local position log shows zero net position with explicit closing fills.
- The execution lifecycle has reached `FLAT_RECONCILING` and then
  `FLAT` (or `ERROR_HALTED` if mismatch / flip occurred).
- Ops on-call has logged the flatten event with timestamp and reason.

---

## 4. ERROR_HALTED recovery

### 4.1 Triggers

ERROR_HALTED is entered automatically on any of:

- Two consecutive `critical` latency alerts within a 60 s window.
- `ClockDriftMonitor` `critical`.
- `OrderStateError` raised by the state machine.
- Broker session disconnect that does not reconnect within the configured
  grace window (TBD-BROKER).
- Position-reconciliation divergence between broker and local state.
- Hard daily-loss tripwire breach.
- Manual operator trigger.

### 4.2 What is preserved

- Full order log, position log, tick log, and monitor alert log up to the
  halt instant.
- The contamination log is flushed and frozen.
- Configuration snapshot at halt time is written under `incidents/<id>/`.
- The strategy registry hash is recorded.

### 4.3 Who is paged

- Primary on-call (Ops).
- Backup on-call (Ops).
- Risk reviewer (independent — see `docs/OWNERS.md`).
- Director Sponsor on `critical` severity or any financial impact > the
  TBD threshold set in `configs/risk_limits.yml`.

### 4.4 Rollback / replay logic

- No automatic rollback of fills. Fills that occurred are real.
- The position is flattened via the §3 protected-flatten sequence:
  protective stop stays working until the broker confirms flat, then the
  remaining OCO leg is cancelled. There is no default cancel-first path.
- If position flips or broker / internal mismatch occurs during the
  sequence, the execution lifecycle is driven to `ERROR_HALTED` and the
  protective stop remains working pending Risk-Reviewer disposition in
  the incident channel.
- For replay analysis, the preserved logs are loaded into the offline
  harness; do not replay against a live session.

### 4.5 Post-incident review

A post-incident review is **required** for every ERROR_HALTED entry. See
`docs/ops/incident_response_template.md`. Review must occur within 5
business days, attended by Engineering, Risk reviewer, and the Director
Sponsor. The system does not return to a tradeable state until the review
sign-off is on file.

---

## 5. On-call coverage

### 5.1 Roster

- Primary on-call: Ops (TBD-OPS, per `docs/OWNERS.md`).
- Backup on-call: Ops backup.
- Risk reviewer is **not** on call for ops alerts; Risk is paged only on
  ERROR_HALTED and on contamination-log incidents.
- Director Sponsor is paged on ERROR_HALTED with material financial impact.

### 5.2 Escalation tree

1. Primary Ops on-call (page).
2. If no ack within 5 minutes: Backup Ops on-call (page).
3. If no ack within 10 minutes total: Engineering lead.
4. If financial impact crosses the configured threshold: Director Sponsor.
5. If contamination-log entry: Risk reviewer.

### 5.3 Hand-off discipline

- Hand-off occurs at a fixed daily time agreed by the Ops team.
- Outgoing on-call posts: open incidents, watch items, any deviations from
  the runbook, and the next scheduled maintenance window.
- Incoming on-call acknowledges in writing. No verbal-only hand-offs.
- A missed hand-off counts as the outgoing on-call remaining responsible
  until acknowledged.

---

## 6. Alert escalation

### 6.1 Severity ladder

| Severity   | Routing                              | Examples                                                                     |
| ---------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| `info`     | Ops chat only                        | Heartbeat, session connect, bar boundary tick                                |
| `warn`     | Ops chat + counter; no page          | LatencyMonitor warn (>= 50 ms); ClockDriftMonitor warn (>= 10 ms); soft tripwire |
| `critical` | Page primary on-call; backup if no ack | LatencyMonitor critical (>= 250 ms); ClockDriftMonitor critical (>= 250 ms); OrderStateError; hard tripwire; broker disconnect beyond grace |
| `page`     | Pages primary + backup + Risk        | ERROR_HALTED entry; reconciliation divergence; contamination-log write during session |

### 6.2 Page targets

- Primary, backup, Risk, and Director Sponsor contacts are listed in
  `docs/OWNERS.md` (currently TBD). All contacts must be filled before paper
  trading is unblocked.
- Pages are sent via the ops paging system (TBD-OPS to select and document).

---

## 7. Blockers

This document is **DRAFT**. The following must all be resolved before this
runbook can be promoted out of draft and before paper trading may begin:

- DRAFT until broker confirmed; paper trading **BLOCKED** until
  **[Appendix F finalized]** for the chosen broker.
- TBD-BROKER items in §1.4, §2, §4.1, §6.2 must be answered against the
  chosen broker (see `docs/ops/broker_specific_questions.md`).
- TBD-OPS owner names in §5 and §6 must be filled in `docs/OWNERS.md`.
- Risk-limit dollar values in §2.4 must be set by the Director Sponsor.
- Vendor confirmation responses (rate sheet, OCO, disconnect behaviour) must
  be on file under `docs/vendor-replies/`.

Appendix I is a scope-control note for this internal-only project (see
`docs/appendices/I_legal_scope_note.md`); it does not gate paper or
internal live trading. Counsel review is required only on a
scope-expansion trigger.

No item in this runbook may be cited as evidence of production-readiness or
broker-specific behaviour while the document remains DRAFT.
