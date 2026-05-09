# Economic Calendar Provider — Selection Criteria & Outbound Request

## What & why

This document combines the selection criteria for our economic-calendar
provider of record with the outbound request we will send to candidate
providers. Per `v1.4r1_errata_and_kickoff.md` §5, no v0.2 backtest may be
approved while macro-event handling is still resting on placeholder data.
Macro releases drive blackout windows in the order-state-machine simulator
(§H.2) and shape the contamination posture for any feature that touches
release minutes; an imprecise release timestamp (or a silently revised one)
can leak future information into training. We therefore need a provider
whose release-time precision is at most one second, whose revision history
is queryable, and whose license terms permit the redistribution we need
inside our own research environment. This file is the source-of-truth for
the criteria we will score candidates against and for the request we will
send today.

## Status table

Status vocabulary: `not_started | requested | received | verified | blocked`.

| Ask                                                       | Status      |
| --------------------------------------------------------- | ----------- |
| Release-time precision (target: <= 1s)                    | not_started |
| Revisions policy (definition, disclosure, frequency)      | not_started |
| Change-history availability (queryable as-of snapshots)   | not_started |
| Coverage — US releases (minimum scope)                    | not_started |
| Coverage — international releases (if relevant)           | not_started |
| API availability (REST / streaming / file drop)           | not_started |
| License terms (internal use, redistribution, retention)   | not_started |
| Sample data feed                                          | not_started |
| SLA for outages                                           | not_started |
| Written reply on file (PDF or signed email)               | not_started |

## Selection criteria

A candidate is acceptable as our economic-calendar provider of record only
if all of the following are satisfied. Each is scored from the written reply
and from the sample feed; nothing is taken on a sales call alone.

1. **Release-time precision.** Published release timestamps must be
   accurate to at most one second relative to the official release source
   (e.g., BLS, BEA, Fed). Vendors who publish only "08:30 ET" without a
   sub-minute timestamp are not acceptable as primary.
2. **Revisions policy.** The vendor must have a written, public revisions
   policy that defines what counts as a revision, when revisions are
   published, and how they are notified. A "we sometimes update values"
   answer is disqualifying.
3. **Change-history availability.** We must be able to query the value of
   any release as of any past timestamp. This is a hard requirement for
   contamination control: a model trained on the post-revision number must
   never be evaluated against the pre-revision number, and vice versa.
4. **Coverage — US releases as minimum scope.** All scheduled US macro
   releases that move S&P futures (CPI, PPI, PCE, NFP / employment
   situation, FOMC statement, FOMC minutes, ISM, retail sales, GDP, jobless
   claims, Treasury auctions where relevant). International releases are
   in-scope only if a strategy variant requires them.
5. **API availability.** A documented REST or streaming API; file-drop is
   acceptable as a fallback but not as the primary integration.
6. **License terms.** Internal research use must be permitted without
   per-seat fees that scale unreasonably; redistribution within the
   research team is required; long-term retention of historical snapshots
   is required for audit.

## Outbound request body

To: [Economic-calendar provider — name TBD]
From: [Sender — Ops]
Subject: Economic calendar — release-time precision, revisions, and license

Hello,

We are evaluating economic-calendar providers of record for a systematic
futures programme trading the US session. The calendar is used to define
blackout windows around macro releases and to control look-ahead bias in
research, so the release-time precision and the revisions / change-history
posture are decisive for us. Please respond in writing — letterhead, signed
email, or a public specification page is acceptable.

### A. Release-time precision

1. Confirm the release-time precision you publish for US macro releases.
   Our requirement is at most one second relative to the official release.
   If your precision differs by release type (e.g., FOMC vs. NFP vs. ISM),
   state each.
2. State the source of your release timestamp: do you take it directly
   from the official source's public dissemination, from an exchange
   feed, from a wire (e.g., a major newswire), or from your own
   capture? If captured, describe the capture point and any expected
   skew.
3. State the clock-sync mechanism (NTP / PTP) and the time zone of the
   published timestamps.

### B. Revisions and change history

4. Provide your published revisions policy. Define what counts as a
   revision, the typical lag, and the notification mechanism.
5. Confirm whether historical values are queryable as-of any past
   timestamp (i.e., we can ask "what value was published for May CPI as
   of 2024-06-12 09:00 ET?"). This is a hard requirement.
6. State how long the change history is retained.

### C. Coverage

7. List the US macro releases included in your standard feed. We need at
   minimum: CPI, PPI, PCE, NFP / employment situation, FOMC statement and
   minutes, ISM manufacturing and services, retail sales, GDP, jobless
   claims, and Treasury auctions where relevant.
8. List any tiering — i.e., which releases are in the base feed versus
   premium add-ons.
9. State which international releases (if any) are included in the base
   feed.

### D. API and integration

10. Document the API surface: REST, streaming, file drop. Provide the
    base URL of your API documentation.
11. Provide the rate-limit / throughput posture and the authentication
    mechanism.
12. Provide a sample data feed covering at least one US release week, in
    the format we would consume in production.

### E. License and SLA

13. State the license terms for internal research use, redistribution
    inside our research team, and long-term retention of historical
    snapshots.
14. State the published SLA for the API / feed: uptime target,
    notification policy for outages, and the remedy for breach.

### F. Evidence

15. Please attach or link the current published specification, the
    revisions policy page, and the API documentation entry point.

## Footer

- Addressee: [Economic-calendar provider — name TBD]
- Sender: [Sender — Ops], cc Director Sponsor
- Sent date: [unsent]
- Reply due: [sent date + 5 business days]
- Follow-up cadence: nudge at +3 business days; escalate to vendor account
  manager at +7 business days; escalate to Director Sponsor at +10 business
  days.

## Reply on file

_None — request not yet sent._
