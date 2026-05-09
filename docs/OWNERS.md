# Owners — v1.4-r1

**Issued:** 2026-05-09 (Day 0)
**Rule:** No unnamed workstreams. Risk reviewer must be independent of
engineering and quant (v1.0 independence rule). Names below are placeholders
and **must be filled before any code is merged to the spec-named branch.**

| Workstream                                            | Owner   | Backup  |
| ----------------------------------------------------- | ------- | ------- |
| Engineering — data + engine                           | TBD-ENG | TBD-ENG |
| Quant — baselines + validation harness                | TBD-QNT | TBD-QNT |
| Risk reviewer — contamination log + sign-off gate     | TBD-RSK | TBD-RSK |
| Ops — broker / OCO confirmation + Appendix F          | TBD-OPS | TBD-OPS |
| Legal — Appendix I scoping                            | TBD-LGL | TBD-LGL |
| Director sponsor — capital/drawdown values + final approvals | TBD-DIR | TBD-DIR |

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
