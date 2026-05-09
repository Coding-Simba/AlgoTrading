# Broker-Specific Questions — DRAFT

> **DRAFT — broker placeholder. Paper trading is BLOCKED until this document is
> filled out against the chosen broker and signed off (Appendix F).**

**Status:** DRAFT. No broker has been selected.
**Owner:** Ops (TBD-OPS — see `docs/OWNERS.md`).
**Issued:** 2026-05-09.

---

## Purpose

This document is the list of questions that must be answered **against a chosen
broker** before `docs/ops/live_runbook_draft.md` can be promoted from DRAFT and
before paper trading is unblocked per `docs/GATES.md`.

This **complements** the procurement requests under `docs/procurement/`:

- The procurement requests
  (`broker_rate_sheet_request.md`, `oco_confirmation_request.md`,
  `data_vendor_request.md`, `economic_calendar_provider_selection.md`)
  ask vendors for **vendor-published facts** (rate sheets, written
  confirmations, capability statements).
- This document asks for **vendor-confirmed answers attached to the chosen
  broker**: each answer is a written response from the broker, dated, on
  letterhead or signed email, stored under
  `docs/vendor-replies/<broker>-<topic>.md` and referenced here by item
  number.

A question is "answered" only when the response is on file and the answer
field below contains a one-line summary plus the file reference. Verbal
confirmations are not accepted.

---

## 1. Connectivity

1.1 What protocols does the broker support for order entry (FIX, native
binary, REST, vendor SDK)? Which is supported in production?

> Answer: _____________________________

1.2 What is the documented round-trip order-acknowledgement latency from
the colocation facility we will use? Provide p50 and p99.

> Answer: _____________________________

1.3 What is the heartbeat interval and missed-heartbeat policy (number of
missed heartbeats before session is declared dead)?

> Answer: _____________________________

1.4 Are there scheduled maintenance windows? When? Are they communicated
in advance?

> Answer: _____________________________

1.5 What rate limits apply to order entry, modification, and cancellation?
Are they per-session, per-account, per-symbol, or aggregate?

> Answer: _____________________________

1.6 Is there a sandbox / test environment? Is it functionally equivalent
to production for OCO, stop, and disconnect semantics?

> Answer: _____________________________

---

## 2. OCO and stop semantics

2.1 Where does the OCO logic reside: at the exchange, at the broker server,
or platform-local on our side?

> Answer: _____________________________

2.2 If platform-local: what happens to the OCO pair on platform crash,
process restart, or network loss?

> Answer: _____________________________

2.3 If broker-server: what is the failure mode if that server fails over
or restarts? Is the OCO pair preserved?

> Answer: _____________________________

2.4 What is the stop-trigger semantics: trade-print-through, last-trade,
bid/ask touch, or NBBO-based?

> Answer: _____________________________

2.5 What happens if a stop is triggered during a fast market or limit-up /
limit-down condition? Is it converted to a market or to a stop-limit?

> Answer: _____________________________

2.6 Are stops guaranteed against gaps? If not, what is the documented
worst-case slippage observed historically?

> Answer: _____________________________

2.7 Does the broker support attached / bracket orders, and are they atomic
with the parent order?

> Answer: _____________________________

---

## 3. Disconnect and reconnect

3.1 On TCP disconnect with an open session, what happens to working orders?
(Cancel-on-disconnect, leave-working, or session-configurable.)

> Answer: _____________________________

3.2 On disconnect, what happens to OCO pairs specifically?

> Answer: _____________________________

3.3 On disconnect, what happens to attached / bracket children?

> Answer: _____________________________

3.4 On reconnect, can we retrieve the working-order state and recent fill
history? Within what time window?

> Answer: _____________________________

3.5 What sequence-number reset / replay semantics apply on reconnect?

> Answer: _____________________________

3.6 What is the configurable cancel-on-disconnect timeout, if any?

> Answer: _____________________________

---

## 4. Error and halt semantics

4.1 What is the error-code taxonomy? Provide the full list of codes our
session may receive.

> Answer: _____________________________

4.2 Which error codes are retryable? Which require operator intervention?

> Answer: _____________________________

4.3 How are exchange-level halts (regulatory, volatility, news pending)
communicated to our session?

> Answer: _____________________________

4.4 During a halt, can working orders be cancelled? Modified? New orders
submitted (queued for resume)?

> Answer: _____________________________

4.5 What is the resume-from-halt order-state behaviour?

> Answer: _____________________________

4.6 Are there any soft-reject conditions (e.g. "would-cross", "self-match")
and what is their code?

> Answer: _____________________________

---

## 5. Position reconciliation

5.1 What is the canonical position-of-record source: the broker's
end-of-day statement, the intraday API, or both?

> Answer: _____________________________

5.2 What is the format and delivery channel of the end-of-day statement
(file format, time of availability, transport)?

> Answer: _____________________________

5.3 At what time (with timezone) is end-of-day cut?

> Answer: _____________________________

5.4 Are intraday position queries authoritative for reconciliation, or only
indicative?

> Answer: _____________________________

5.5 What is the policy on trade busts, corrections, or adjustments? How
are they communicated and within what window?

> Answer: _____________________________

5.6 What is the commission-attribution timing — per-fill in real time, or
batched at end-of-day?

> Answer: _____________________________

---

## 6. Audit trail and logs

6.1 What is the broker's retention period for order, fill, and session
logs?

> Answer: _____________________________

6.2 Can we retrieve full session logs on demand? In what format?

> Answer: _____________________________

6.3 Are exchange-stamped timestamps available for every fill? With what
precision?

> Answer: _____________________________

6.4 What is the regulatory audit-trail compliance posture (CAT, OATS,
equivalent for futures)?

> Answer: _____________________________

6.5 Is there a separate clock-source statement we can rely on to validate
our `ClockDriftMonitor` reference?

> Answer: _____________________________

---

## 7. Support contact

7.1 Who is our named account manager? Provide name, email, phone.

> Answer: _____________________________

7.2 What are the support hours? Are there 24x7 channels for production
issues?

> Answer: _____________________________

7.3 What is the documented SLA for support response by severity?

> Answer: _____________________________

7.4 Where is support escalation documented (to manager, to head of trading
desk, to compliance)?

> Answer: _____________________________

---

## 8. Incident contact

8.1 What is the broker's incident hotline for trading-desk emergencies
(stuck orders, mis-routed fills, suspected outages)?

> Answer: _____________________________

8.2 What is the broker's policy on operator-initiated cancel-all from the
broker side (we ask the broker to flatten)?

> Answer: _____________________________

8.3 What is the broker's communication protocol during their own outages
(status page, email, phone)?

> Answer: _____________________________

8.4 Who is the named compliance contact for any post-incident review that
involves a regulator?

> Answer: _____________________________

8.5 What is the policy for trade-bust / break requests on our side, and
within what window must they be filed?

> Answer: _____________________________

---

## Promotion criteria

This document is "complete" only when **every numbered item** has a written
answer attached to a vendor-reply file, and Ops + Risk have signed off.
Until then:

- `docs/ops/live_runbook_draft.md` remains DRAFT.
- Paper trading remains **BLOCKED** per `docs/GATES.md`.
- No live trading may begin under any circumstance.

This document is itself **DRAFT**.
