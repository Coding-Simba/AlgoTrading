# Data Vendor Request — Primary and Secondary

## What & why

This is the outbound request to two independent historical-data vendors for
MES tick and BBO data. The primary supplies the production research feed; the
secondary is a cross-check, not a redundancy — it must source from a
different upstream feed where possible so that timestamp, gap, and revision
disagreements are detectable. The cross-check is required by our
contamination and data-quality posture; without it, a single vendor's gap or
silent revision can invalidate a backtest result undetected. Replies feed the
data-ingestion skeleton (Sprint 1 item 2), the tick + BBO parser (item 4),
and the bar-builder boundary tests (item 5, per §B.5).

Note explicitly: the secondary vendor is required as an **independent
cross-check** — different upstream feed if possible — not as hot-standby
redundancy.

---

## Vendor 1 — Primary

### Status table

Status vocabulary: `not_started | requested | received | verified | blocked`.

| Ask                                              | Status      |
| ------------------------------------------------ | ----------- |
| MES historical tick data availability            | not_started |
| MES historical BBO data availability             | not_started |
| History depth (years)                            | not_started |
| Gap policy (definition, disclosure, fill rule)   | not_started |
| Corporate-action handling (if applicable to MES) | not_started |
| Tick precision                                   | not_started |
| Timestamp source (exchange vs. vendor)           | not_started |
| Revisions / corrections policy                   | not_started |
| Sample data file                                 | not_started |
| Pricing tiers                                    | not_started |
| SLA for outages                                  | not_started |

### Request body — Primary

To: [Primary vendor — name TBD]
From: [Sender — Ops]
Subject: MES tick + BBO historical data — specification and quote

Hello,

We are evaluating historical-data vendors for a systematic futures programme
on Micro E-mini S&P (MES). Please provide written answers to the following
and a sample file for each data type.

1. Confirm availability of historical tick (trade) data for MES, and the
   earliest available date.
2. Confirm availability of historical BBO (best bid / best offer) data for
   MES, and the earliest available date.
3. State the total history depth in years for each data type.
4. Gap policy: how do you define a gap, how are gaps disclosed in the file
   (sentinel value, separate manifest, etc.), and what is your rule for
   filling vs. leaving missing intervals?
5. Corporate-action handling: state whether any corporate-action adjustments
   apply to MES (we expect none for the front-month future, but please
   confirm) and how roll dates are handled in continuous-contract files
   if you provide one.
6. Tick precision: state the price precision (e.g., 0.25) and any
   sub-tick fields if present.
7. Timestamp source: are timestamps taken directly from the CME exchange
   feed, or are they re-stamped at your gateway? State the precision
   (microsecond / nanosecond) and the clock-sync mechanism.
8. Revisions / corrections policy: are historical files revised after
   publication? If yes, how are revisions notified, and can we pin to an
   immutable as-of snapshot?
9. Provide a sample data file (one trading session of MES tick + BBO is
   sufficient) so we can validate format and parser.
10. Pricing tiers: list the tiers, the volume / user / symbol axes, and any
    redistribution constraints.
11. SLA for outages: state the published SLA for the historical download
    service and the live feed if applicable.

---

## Vendor 2 — Secondary (independent cross-check)

### Status table

Status vocabulary: `not_started | requested | received | verified | blocked`.

| Ask                                              | Status      |
| ------------------------------------------------ | ----------- |
| Independence of upstream feed from primary       | not_started |
| MES historical tick data availability            | not_started |
| MES historical BBO data availability             | not_started |
| History depth (years)                            | not_started |
| Gap policy (definition, disclosure, fill rule)   | not_started |
| Corporate-action handling (if applicable to MES) | not_started |
| Tick precision                                   | not_started |
| Timestamp source (exchange vs. vendor)           | not_started |
| Revisions / corrections policy                   | not_started |
| Sample data file                                 | not_started |
| Pricing tiers                                    | not_started |
| SLA for outages                                  | not_started |

### Request body — Secondary

To: [Secondary vendor — name TBD]
From: [Sender — Ops]
Subject: MES tick + BBO historical data — independent cross-check source

Hello,

We are sourcing MES historical tick and BBO data from a primary vendor and
need a second, independent source for cross-checking. The intent is **not**
hot-standby redundancy; the intent is to detect silent gaps, timestamp
drift, and undisclosed revisions by diffing two independent files.

Before we go further, please confirm item 1 below; the remaining items
mirror our primary-vendor request.

1. Independence: please describe your upstream source for CME / MES data.
   We are looking for a feed that is not derived from the same upstream as
   [Primary vendor — name TBD]. If your feed shares an upstream, say so —
   that is disqualifying for this role but useful for us to know.
2. Confirm availability of historical tick data for MES, and the earliest
   available date.
3. Confirm availability of historical BBO data for MES, and the earliest
   available date.
4. State the total history depth in years for each data type.
5. Gap policy: definition, disclosure mechanism, fill rule.
6. Corporate-action handling for MES, and roll-date handling for any
   continuous-contract product.
7. Tick precision and any sub-tick fields.
8. Timestamp source and precision; clock-sync mechanism.
9. Revisions / corrections policy and as-of pinning.
10. Sample data file (one trading session of MES tick + BBO).
11. Pricing tiers and redistribution constraints.
12. SLA for outages.

## Footer

- Addressees: [Primary vendor — name TBD]; [Secondary vendor — name TBD]
- Sender: [Sender — Ops], cc Director Sponsor
- Sent date: [unsent]
- Reply due: [sent date + 5 business days]
- Follow-up cadence: nudge at +3 business days; escalate to vendor account
  manager at +7 business days; escalate to Director Sponsor at +10 business
  days.

## Reply on file

_None — requests not yet sent._
