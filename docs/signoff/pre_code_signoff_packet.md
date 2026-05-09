# Pre-code sign-off packet — v1.4-r1

**Status:** Cover sheet for the Phase 1 (pre-code) sign-off review.
**Issued:** 2026-05-09
**Owner:** Director Sponsor
**Required for gate:** v0.2 strategy code (per `docs/GATES.md`).
**Forbidden until signed:** any v0.2 signal logic, B.7 / B.8 entry rules, EMA /
VWAP / ATR helpers wired to v0.2. Enforcement: `tests/test_sprint1_freeze.py`.

This packet collects the artifacts that must carry signatures before v0.2
strategy code may be merged. Nothing in this packet modifies the strategy
spec; it is packaging for the existing appendices, the Director-set risk
values, and the three-partition lock.

---

## 1. Scope

The Phase 1 sign-off review covers, and **only** covers:

- The five FROZEN pre-code appendices: B, C, D (placeholders permitted for
  framework only), E, H (errata §3).
- The six Director-set risk values landing in `configs/risk_limits.yml`.
- The three-partition date ranges landing in `configs/data_partitions.yml`
  (§C.9 lock; §B.13 registry-first rule per errata §6).

Subsequent gates — broker rate sheet substitution, Appendix F, Appendix I
counsel sign-off, validation freeze, paper transition, small-size live,
Appendix G, scale-up — are **out of scope** for this packet and are signed
at their respective phase gates.

## 2. Appendix sign-off rows

Signer roles mirror `docs/OWNERS.md` and `configs/signoff_matrix.yml`. The
"Required for" gate is "v0.2 strategy code" for every row in this section.
"Unblocks" entries are taken from `docs/GATES.md`.

| ID | Title                                                          | Signer role        | Detail / checklist                                                | Unblocks once signed                            |
| -- | -------------------------------------------------------------- | ------------------ | ----------------------------------------------------------------- | ----------------------------------------------- |
| B  | Strategy specification & registry rules                        | Director sponsor   | `docs/appendices/B_strategy_spec_v0_2.md`                         | v0.2 strategy code (joint with C, D, E, H)      |
| C  | Data partition & contamination protocol                        | Risk reviewer      | `docs/appendices/C_data_qa_partitioning.md`                       | v0.2 strategy code (joint with B, D, E, H)      |
| D  | Fill model (placeholders permitted for framework only)         | Engineering        | `docs/appendices/D_fill_model.md`                                 | v0.2 strategy code (joint with B, C, E, H)      |
| E  | Validation, paper, and live transition criteria                | Quant              | `docs/appendices/E_quant_gates.md`                                | v0.2 strategy code (joint with B, C, D, H)      |
| H  | Order state machine                                            | Engineering        | `docs/appendices/H_execution_ops.md`                              | v0.2 strategy code (joint with B, C, D, E)      |

## 3. Director-set risk values

Six values, all signed by the Director Sponsor. Defaults are unsigned. They
land in `configs/risk_limits.yml` and are validated by the governance guard.
Director Sponsor and Risk Reviewer must be distinct individuals
(`docs/OWNERS.md` independence rule).

| Value                                  | Signer role       | Units                | Default state |
| -------------------------------------- | ----------------- | -------------------- | ------------- |
| allocated_capital_usd                  | Director Sponsor  | USD (number, > 0)    | unsigned      |
| max_oos_drawdown_pct                   | Director Sponsor  | percent in (0, 100)  | unsigned      |
| max_acceptable_losing_streak           | Director Sponsor  | int, >= 1            | unsigned      |
| daily_loss_limit_usd                   | Director Sponsor  | USD (number, > 0)    | unsigned      |
| aggregate_program_drawdown_limit_pct   | Director Sponsor  | percent in (0, 100)  | unsigned      |
| risk_of_ruin_threshold_pct             | Director Sponsor  | percent in (0, 100)  | unsigned      |

The Director Sponsor records values into
`docs/signoff/director_values_template.md` first; the values are then
copied into `configs/risk_limits.yml` and signed (`locked: true`).

## 4. Three-partition date ranges

The lock template is `configs/data_partitions.yml`. The §C.9 lock binds the
training, validation, and final-holdback date ranges. Once committed,
edits require a Change Request. Until the lock is signed, the contamination
guard rejects any attempt to query the validation partition.

Per errata §6, the controlling rule for v0.3 OOS reuse is **§B.13**
(registry-first): the v0.2 OOS partition is clean for v0.3 only if v0.3
rules were registered in `src/algotrading/registry/registry.py` **before**
the v0.2 OOS query was run. §C.9 wording defers to §B.13.

| Partition       | Source field                              | Default state |
| --------------- | ----------------------------------------- | ------------- |
| training        | `partitions.training.{start,end}`         | empty         |
| validation      | `partitions.validation.{start,end}`       | empty         |
| final_holdback  | `partitions.final_holdback.{start,end}`   | empty         |

## 5. Acceptance criteria for v0.2 unblock

All of the following must hold before v0.2 strategy code may be merged:

1. Every appendix row in §2 carries a signature and
   `configs/signoff_matrix.yml` shows `signed: true` for ids B, C, D, E, H.
2. `configs/risk_limits.yml` carries non-empty values for all six fields,
   plus `locked: true`, `signed_by` (Director Sponsor identifier, distinct
   from the Risk Reviewer), and `signed_at_iso` (ISO-8601).
3. `configs/data_partitions.yml` carries non-empty start/end for all three
   partitions, plus `locked: true`, `locked_by`, and `locked_at_iso`.
4. The Risk Reviewer has counter-signed certifying independence per
   `docs/OWNERS.md`.
5. CI gate is all-green: `tests/test_phase1_gate.py` and the matrix
   defined by `configs/signoff_matrix.yml` pass; the freeze guard
   `tests/test_sprint1_freeze.py` continues to pass.

If any of the above is missing, the gate state remains "Now" and v0.2
strategy code remains FORBIDDEN.

## 6. Consolidated sign-off block

Empty by default. Each row is filled by the named signer on the same PR
that flips the matching value in `configs/signoff_matrix.yml`,
`configs/risk_limits.yml`, or `configs/data_partitions.yml`.

### 6.1 Appendix signatures

| Appendix | Signer name | Role               | Date (ISO-8601) | Notes |
| -------- | ----------- | ------------------ | --------------- | ----- |
| B        |             | Director Sponsor   |                 |       |
| C        |             | Risk Reviewer      |                 |       |
| D        |             | Engineering        |                 |       |
| E        |             | Quant              |                 |       |
| H        |             | Engineering        |                 |       |

### 6.2 Director-set values signature

| Field                     | Value |
| ------------------------- | ----- |
| Signer name               |       |
| Role                      | Director Sponsor |
| Date (ISO-8601)           |       |
| Source document           | `docs/signoff/director_values_template.md` |
| Target config             | `configs/risk_limits.yml` |
| Notes                     |       |

### 6.3 Partition lock signature

| Field                     | Value |
| ------------------------- | ----- |
| Signer name               |       |
| Role                      | Director Sponsor |
| Date (ISO-8601)           |       |
| Target config             | `configs/data_partitions.yml` |
| §B.13 registry-first ack  |       |
| Notes                     |       |

### 6.4 Risk Reviewer counter-sign (independence)

| Field                                                           | Value |
| --------------------------------------------------------------- | ----- |
| Signer name                                                     |       |
| Role                                                            | Risk Reviewer |
| Date (ISO-8601)                                                 |       |
| Independence ack (not Engineering / Quant / Director Sponsor)   |       |
| Confirms appendix C signature is by this same Risk Reviewer     |       |
| Notes                                                           |       |

*End of pre-code sign-off packet.*
