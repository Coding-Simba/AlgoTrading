# Owners — v1.4-r1

**Issued:** 2026-05-09 (Day 0)
**Rule:** No unnamed workstreams. Risk reviewer must be independent of
engineering and quant (v1.0 independence rule).

Public repo uses pseudonymous owner IDs for privacy. **These IDs are not
placeholders.** The private real-name mapping is held off-repo by the
Director Sponsor and Risk Reviewer. No real names are committed publicly.

Risk-review independence is enforced by role ID. `RISK-*` may not also
act as `ENG-*` or `QUANT-*` for the same approval gate.

| Workstream                                            | Owner    | Backup           |
| ----------------------------------------------------- | -------- | ---------------- |
| Engineering — data + engine                           | ENG-01   | ENG-02-BACKUP    |
| Quant — baselines + validation harness                | QUANT-01 | QUANT-02-BACKUP  |
| Risk reviewer — contamination log + sign-off gate     | RISK-01  | RISK-02-BACKUP   |
| Ops — broker / OCO confirmation + Appendix F          | OPS-01   | OPS-02-BACKUP    |
| Legal scope note                                      | LEGAL-01 | LEGAL-02-BACKUP  |
| Director sponsor — capital / drawdown values          | DIR-01   | DIR-02-BACKUP    |

## Independence rules

- `RISK-*` may not also hold `ENG-*`, `QUANT-*`, or `DIR-*` on the same
  family / approval gate.
- The Director Sponsor (`DIR-*`) signs capital and drawdown values; the
  Risk Reviewer (`RISK-*`) signs the contamination log and the sign-off
  gate. These two roles must be distinct individuals.

## How to update this file

This file is the single source of truth for ownership. Changes require:

1. A pull request labelled `owners-change`.
2. Risk reviewer ack (independence check).
3. Director Sponsor ack.

Do not store names in any other file.
