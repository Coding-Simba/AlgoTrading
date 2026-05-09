# Owners — v1.4-r1

**Issued:** 2026-05-09 (Day 0)
**Rule:** No unnamed workstreams. Risk reviewer must be independent of
engineering and quant (v1.0 independence rule). Names below are placeholders
and **must be filled before any code is merged to the spec-named branch.**

Owner identifiers below are pseudonymous IDs (per Risk Reviewer guidance:
not "TBD"). Each ID maps 1:1 to a single named individual whose mapping is
held by the Director Sponsor and the Risk Reviewer separately. A backup ID
is a different individual from the primary ID for the same workstream.

| Workstream                                            | Owner    | Backup    |
| ----------------------------------------------------- | -------- | --------- |
| Engineering — data + engine                           | ENG-01   | ENG-02    |
| Quant — baselines + validation harness                | QUANT-01 | QUANT-02  |
| Risk reviewer — contamination log + sign-off gate     | RISK-01  | RISK-02   |
| Ops — broker / OCO confirmation + Appendix F          | OPS-01   | OPS-02    |
| Legal — Appendix I scoping                            | LEGAL-01 | LEGAL-02  |
| Director sponsor — capital/drawdown values + final approvals | DIR-01   | DIR-02    |

## Independence rules

- Risk reviewer **may not** also hold the Engineering, Quant, or Director
  Sponsor role on the same family.
- The Director Sponsor signs capital and drawdown values; Risk reviewer signs
  the contamination log and the sign-off gate. These two signers must be
  distinct individuals.

## How to update this file

This file is the single source of truth for ownership. Changes require:

1. A pull request labelled `owners-change`.
2. Risk reviewer ack (independence check).
3. Director Sponsor ack.

Do not store names in any other file.
