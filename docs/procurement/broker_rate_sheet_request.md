# Broker Rate Sheet & Order-Handling Request

## What & why

This is the outbound request to our prospective futures broker for a complete,
written rate sheet and a written description of order-handling behaviour for
MES on CME Globex. Per `v1.4r1_errata_and_kickoff.md` §5, no v0.2 strategy
backtest, validation, or OOS run may be approved while costs in §D.2 are still
placeholders. The replies to this request are the source-of-truth that retire
those placeholders. The order-handling answers (stop-trigger convention, OCO
residence, disconnect behaviour) feed Appendix D fill-model assumptions and
the order-state-machine simulator (§H.2); without written confirmation those
modules cannot be locked.

## Status table

Status vocabulary: `not_started | requested | received | verified | blocked`.

| Ask                                                    | Status      |
| ------------------------------------------------------ | ----------- |
| Commission per side per contract (MES)                 | not_started |
| Exchange fees (CME)                                    | not_started |
| Clearing fees                                          | not_started |
| NFA fee                                                | not_started |
| Platform / routing fees                                | not_started |
| All-in tick cost (round-turn, MES)                     | not_started |
| Volume tier schedule (if any)                          | not_started |
| Stop-trigger convention (last / bid-ask / NBBO)        | not_started |
| OCO residence (server / exchange / platform-local)     | not_started |
| OCO redundancy and failure modes                       | not_started |
| Disconnect behaviour — working orders                  | not_started |
| Disconnect behaviour — OCO pairs                       | not_started |
| Disconnect behaviour — stops                           | not_started |
| Reconnect semantics and client identification          | not_started |
| Written confirmation (PDF or signed email) on file     | not_started |

## Request body

To: [Broker — name TBD], Institutional / API Desk
From: [Sender — Ops]
Subject: MES rate sheet and order-handling specification — written request

Hello,

We are completing pre-trade due diligence for a systematic futures programme
trading Micro E-mini S&P (MES) on CME Globex via your API. We need written
answers to the items below before our backtest cost model can be approved
internally. Please respond on letterhead, by signed email, or by reference to
a current public specification page; screenshots of internal admin panels are
acceptable as supporting evidence but not as the primary answer.

### A. Costs (per side, per contract, MES)

1. Commission per side, per contract.
2. Exchange fees charged by CME for MES (member / non-member as applicable).
3. Clearing fees.
4. NFA fee.
5. Platform fee, routing fee, and any data / connectivity fee that applies
   per executed contract or per session.
6. The implied all-in cost per round-turn, expressed both in USD and in MES
   ticks (MES tick = 0.25 index points = $1.25 per contract).
7. Volume-tier schedule, if any: thresholds, rates, and the measurement
   window (daily / monthly / rolling).

### B. Stop-trigger convention

8. For a stop-market order on MES, please state explicitly which price
   triggers the stop: last trade, best bid / best ask, NBBO, or another
   reference. If the convention differs for buy stops vs. sell stops, state
   each.
9. Confirm whether this convention is configurable per order, per account,
   or fixed at the platform level.

### C. OCO residence and redundancy

10. Where does the OCO (one-cancels-other) live: at your server, at the
    exchange, or in the platform / client process?
11. If OCO is server-resident, describe the redundancy posture (active /
    active, active / passive, single node) and the documented failure modes.
12. If OCO is platform-local, state explicitly that the OCO does not survive
    a client process death and describe any mitigation offered.

### D. Disconnect and reconnect behaviour

13. On TCP / session loss between client and your gateway, what happens to:
    (a) working limit and stop orders, (b) OCO pairs, (c) stop-loss orders
    that are part of a bracket?
14. Is there a configurable "cancel-on-disconnect" setting? What is the
    default?
15. Reconnect semantics: how is the client identified on reconnect (session
    ID, account, FIX SenderCompID, API key)? Are open orders re-streamed?
    Are duplicate-submission protections in place (idempotency keys, client
    order IDs)?
16. What is the maximum heartbeat interval before the gateway treats the
    session as dead?

### E. Evidence

17. Please attach or link the current published rate sheet and the
    order-handling specification. If any answer above is governed by an
    NDA, indicate so and we will counter-sign.

## Footer

- Addressee: [Broker — name TBD], Institutional / API Desk
- Sender: [Sender — Ops], cc Director Sponsor
- Sent date: [unsent]
- Reply due: [sent date + 5 business days]
- Follow-up cadence: nudge at +3 business days; escalate to sales lead at
  +7 business days; escalate to Director Sponsor at +10 business days.

## Reply on file

_None — request not yet sent._
