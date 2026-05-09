# End-of-Day Reconciliation Checklist — DRAFT

> **DRAFT — broker placeholder. Paper trading is BLOCKED until this checklist
> is broker-specific and signed (Appendix F).**

**Status:** DRAFT.
**Owner:** Ops (TBD-OPS — see `docs/OWNERS.md`).
**Issued:** 2026-05-09.

---

## Purpose

End-of-day reconciliation ensures the local view of the trading day matches
the broker's view of the trading day. Any mismatch is treated as a fault
condition — see the decision rule at the bottom.

This checklist is **DRAFT**. The broker statement format, delivery channel,
and timing are all TBD-BROKER and are listed as questions in
`docs/ops/broker_specific_questions.md`. Until the broker is selected and
those answers are on file, this checklist describes intent only and cannot
be relied on for any live or paper trading. Paper trading is **BLOCKED**
per `docs/GATES.md`.

---

## When to run

- After the broker's documented end-of-day cut. The cut time and timezone
  are TBD-BROKER (question 5.3 in `broker_specific_questions.md`).
- Before the next trading session begins.
- A skipped or incomplete reconciliation blocks the next session's startup
  checklist (see `docs/ops/live_runbook_draft.md` §1.4).

---

## Inputs required

- Local order log for the session (`logs/orders/<date>.jsonl`).
- Local position log snapshots (`logs/positions/<date>.jsonl`).
- Local fill log (`logs/fills/<date>.jsonl`).
- Local commission attribution (`logs/commissions/<date>.jsonl`).
- Local P&L (`logs/pnl/<date>.jsonl`).
- Broker end-of-day statement (TBD-BROKER format and delivery).
- Broker fills file (TBD-BROKER).
- Contamination log entries for the date
  (`src/algotrading/contamination/log.py`).

---

## 1. Position reconciliation

Goal: every working contract count and every held position matches the
broker statement count.

- [ ] Pull final positions from the broker end-of-day statement.
- [ ] Pull final positions from the local position log at session close.
- [ ] For each symbol: local net qty == broker net qty.
- [ ] For each symbol: local long-leg qty == broker long-leg qty (if
      reported separately).
- [ ] For each symbol: local short-leg qty == broker short-leg qty (if
      reported separately).
- [ ] No symbol present on broker side that is absent locally.
- [ ] No symbol present locally that is absent on broker side.
- [ ] Working contract count = 0 unless an explicit overnight order is
      authorised by Risk and recorded in the daily ops log.

PASS criterion: every line above ticks. Any single failure triggers the
decision rule.

---

## 2. Fills reconciliation

Goal: fill price, fill timestamp, and fill quantity match the local order
log on a per-fill basis.

- [ ] Number of fills in local fill log == number of fills in broker fills
      file.
- [ ] Each broker fill matches a local fill on `(symbol, side, qty,
      price, ts)` within the documented timestamp tolerance (TBD-BROKER —
      see question 6.3).
- [ ] No local fill is unmatched on the broker side.
- [ ] No broker fill is unmatched on the local side.
- [ ] Order-state-machine history for each filled order shows a valid
      transition path:
      `NEW -> PENDING_NEW -> WORKING -> [PARTIAL_FILL]* -> FILLED`,
      per `src/algotrading/orders/state_machine.py`.
- [ ] Any cancelled order's history terminates in `CANCELED`, `REJECTED`,
      or `EXPIRED` — never `WORKING` at end-of-day.
- [ ] Any partial fill's accumulated `qty_filled` equals the sum of its
      child fills.

PASS criterion: every fill matches. Any single failure triggers the
decision rule.

---

## 3. Commission reconciliation

Goal: per-fill cost matches the broker statement, and no placeholder cost
has leaked into a real trading record.

- [ ] For each fill: local commission == broker commission for that fill,
      to the documented precision.
- [ ] Per-fill exchange / clearing / NFA / platform fees match line by
      line if itemised by the broker.
- [ ] Sum of per-fill commission == aggregate commission on the broker
      end-of-day statement.
- [ ] **No fill-attribution record carries the `D2_PLACEHOLDER` tag.**
      The constant is defined as `D2_PLACEHOLDER_TAG` in
      `src/algotrading/fillmodel/model.py`. Any record where
      `FillResult.is_placeholder()` is true (or where any log field equals
      `D2_PLACEHOLDER`) is a hard fail: it indicates that placeholder
      costs from §D.2 have leaked into a path that should be using
      broker-confirmed costs. This violates errata §5 and `docs/GATES.md`
      and triggers the decision rule unconditionally.
- [ ] Reconciled commission total is fed back into the local commission
      log as the canonical value for the date.

PASS criterion: every line above ticks **and** no `D2_PLACEHOLDER` tag is
present.

---

## 4. P&L reconciliation

Goal: realised and unrealised P&L computed locally match the broker
statement within the documented precision.

- [ ] Local realised P&L for the session == broker realised P&L for the
      session.
- [ ] Local unrealised P&L at close == broker unrealised P&L at close
      (mark-to-market against the broker's settlement price).
- [ ] Local total P&L == broker total P&L for the session.
- [ ] Per-symbol P&L attribution matches.
- [ ] Mark-to-market settlement price source is the broker's documented
      settlement (not the last-trade price).
- [ ] No P&L record uses placeholder fill costs (cross-check with §3).
- [ ] Cumulative-to-date P&L is updated and the prior-day baseline is
      preserved.

PASS criterion: P&L matches within the documented broker precision (TBD).
Outside that band is a fail and triggers the decision rule.

---

## 5. Cash balance check

- [ ] Starting cash balance == broker statement starting balance.
- [ ] Ending cash balance == broker statement ending balance.
- [ ] Net change in cash == realised P&L net of commissions and fees for
      the session.
- [ ] Margin requirement reported by the broker is within the configured
      cap.
- [ ] Any cash movement not attributable to trading activity (deposits,
      withdrawals, fee adjustments, dividends if applicable) is itemised
      and cross-referenced to the originating record.

PASS criterion: every line above ticks.

---

## 6. Contamination log review

Goal: any contamination-log entry written during the session is reviewed
before the next session begins.

- [ ] List all contamination-log entries dated within the session (use
      `src/algotrading/contamination/log.py` reader).
- [ ] For each entry: confirm the entry is well-formed (event type,
      strategy / family, partition affected, evidence reference).
- [ ] For each entry: confirm Risk Reviewer has been notified.
- [ ] For each entry: confirm whether the entry blocks any pending gate
      transition (per `docs/GATES.md`).
- [ ] Zero unresolved contamination-log entries at the end of
      reconciliation, **or** every unresolved entry has a documented
      Risk-Reviewer follow-up with an owner and date.

PASS criterion: every entry is reviewed and either resolved or owned with
a follow-up date.

---

## Decision rule

If **any** reconciliation item above fails:

1. Move the system to `ERROR_HALTED` immediately. See
   `docs/ops/live_runbook_draft.md` §4.
2. Open an incident record using
   `docs/ops/incident_response_template.md`.
3. Page the on-call per the severity ladder
   (`live_runbook_draft.md` §6).
4. Do **not** attempt to "patch" the local logs to match the broker
   statement. The local logs are append-only evidence; corrections are
   recorded as new entries that reference the divergence, never by
   overwrite.
5. Do **not** start the next session's startup checklist until the
   incident is closed and Risk has signed off.

A reconciliation pass is recorded under
`docs/ops/reconciliation/<date>.md` with the operator's name and the
timestamp of completion. A reconciliation fail is recorded as the
incident record, not as a reconciliation pass.

---

## Blocker note

This checklist is **DRAFT**. The broker statement format, delivery
channel, timing, precision, and per-fee attribution are all TBD-BROKER
and must be answered against the chosen broker before this checklist
becomes operational. Until then:

- Paper trading is **BLOCKED** per `docs/GATES.md`.
- Live trading is **BLOCKED** unconditionally.
- This document may not be cited as evidence of a working reconciliation
  process.
