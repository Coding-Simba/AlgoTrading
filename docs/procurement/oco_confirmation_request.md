# OCO / Server-Side Confirmation Request

## What & why

This is a standalone outbound request for written confirmation of how OCO
(one-cancels-other) orders are handled by our prospective broker. It is
separated from the broader rate-sheet request because the OCO answer is a
hard input to the order-state-machine simulator (§H.2) and to the fill model
(Appendix D), and because a wrong assumption here invalidates every bracket
test and every stop-out path in the backtest. Per
`v1.4r1_errata_and_kickoff.md` §5, no approved v0.2 backtest may rely on
placeholder behaviour for these mechanics. We need written evidence —
specification text, API documentation, or a signed email — not a verbal
assurance from a sales contact.

## Status table

Status vocabulary: `not_started | requested | received | verified | blocked`.

| Ask                                                       | Status      |
| --------------------------------------------------------- | ----------- |
| Where the OCO lives (server / exchange / platform-local)  | not_started |
| What survives a client disconnect                         | not_started |
| Behaviour if the platform process dies                    | not_started |
| Behaviour on partial fills of one leg                     | not_started |
| Idempotency on reconnect (duplicate-submission guard)     | not_started |
| Evidence: screenshots of admin / order ticket             | not_started |
| Evidence: specification page reference                    | not_started |
| Evidence: API documentation reference                     | not_started |
| Written reply on file (PDF or signed email)               | not_started |

## Request body

To: [Broker — name TBD], Institutional / API Desk
From: [Sender — Ops]
Subject: Written confirmation of OCO handling for MES on CME Globex

Hello,

Following up specifically on OCO (one-cancels-other) order handling. We need
written, attributable answers to each of the following before we can lock our
order-state-machine model. Please reply on letterhead, by signed email, or
with explicit references to your current public specification or API docs.

### A. OCO residence

1. Where exactly is the OCO relationship enforced: at the exchange (native
   exchange OCO), at your broker server, or in the platform / client
   process? If different OCO types are offered (e.g., bracket vs. stand-
   alone OCO), state the residence for each.
2. If OCO is enforced at your server, describe the redundancy posture
   (single node, active / passive, active / active) and the documented
   failure modes that could leave one leg working without its sibling.
3. If OCO is enforced platform-local, state this explicitly and describe
   any mitigation (e.g., server-side cancel-on-disconnect on the orphan
   leg).

### B. Survival under client disconnect

4. If the client (our process) loses its TCP / session connection, do the
   OCO pair and any associated stops remain working at the broker / exchange?
5. If "yes," for how long? Is there a session timeout that converts working
   orders to cancelled?
6. Is there a configurable cancel-on-disconnect for the OCO pair? What is
   the default?

### C. Survival under platform process death

7. If your platform process (not the client) dies or is restarted, what
   happens to OCO pairs that were live at the moment of failure? Specifically:
   does the surviving leg become an orphan working order, is it cancelled,
   or is the OCO relationship rebuilt automatically on platform recovery?
8. State the worst-case window during which a surviving leg could fill
   without its sibling being cancelled.

### D. Partial fills

9. On a partial fill of one OCO leg, what happens to the sibling: is its
   working quantity reduced proportionally, cancelled in full, or
   unchanged? State the exact rule.
10. Does the answer differ for stop-limit vs. stop-market siblings?

### E. Idempotency on reconnect

11. On client reconnect, how is the OCO pair re-identified — by client
    order ID, server-assigned OCO group ID, both?
12. If we re-submit an OCO that the server believes is already live (e.g.,
    because our acknowledgement was lost), is the duplicate rejected,
    deduplicated, or accepted as a new pair? State the exact rule.
13. What client-order-ID format do you require, and what is the uniqueness
    window?

### F. Evidence requested

14. Screenshots of the order-ticket UI showing the OCO option as configured.
15. Reference to the relevant page(s) in your published specification.
16. Reference to the relevant section(s) in your API documentation.

## Footer

- Addressee: [Broker — name TBD], Institutional / API Desk
- Sender: [Sender — Ops], cc Director Sponsor
- Sent date: [unsent]
- Reply due: [sent date + 5 business days]
- Follow-up cadence: nudge at +3 business days; escalate to sales lead at
  +7 business days; escalate to Director Sponsor at +10 business days.

## Reply on file

_None — request not yet sent._
