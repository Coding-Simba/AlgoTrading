# Validation freeze checklist

**Owner:** Risk Reviewer (independent — see `docs/OWNERS.md`)
**When used:** Once per `strategy_version`, immediately before the
validation / OOS partition is opened for the first time. After this
checklist is signed and the corresponding row is appended to the
contamination log, the validation guard
(`src/algotrading/contamination/enforcement.py:51`) will permit the harness
to read the partition for that version exactly once.
**Status of file:** Authoritative. The `validation_freeze` row in
`configs/signoff_matrix.yml` may not be marked signed unless every check
below resolves to PASS with documented evidence.

This checklist is read alongside:

- `docs/research_contamination_log/README.md` — schema for the freeze row.
- `docs/v1.4r1_errata_and_kickoff.md` — §5 (broker rate sheet) and §6
  (§B.13 / §C.9 alignment).
- `docs/GATES.md` — gate state machine.

Each item is falsifiable. The reviewer records PASS / FAIL and an
evidence pointer (file path + line, command output, or registry
`entry_id`).

---

## 1. Strategy version is registered before this freeze

- [ ] An entry exists in the strategy registry whose `strategy_version`
      matches the version being frozen, and whose `registered_at` is
      strictly earlier than the proposed freeze timestamp.
      Inspect via
      `StrategyRegistry.latest_for_version(version)`
      (`src/algotrading/registry/registry.py:98`).
- [ ] `StrategyRegistry.validate()`
      (`src/algotrading/registry/registry.py:161`) returns an empty list.
- [ ] The registry entry's `rules_hash`
      (`src/algotrading/registry/registry.py:51-53`) matches the rules
      currently checked into source. Any post-registration rule edit must
      have produced a new registry append (with `supersedes` set) prior
      to this freeze.

**Falsifier:** absence of a registry entry, registry validation errors,
or a rules-hash mismatch between the latest registry entry and source.
§B.13 (canonical per errata §6) requires registry-first rule recording.

## 2. All training-period work is logged

- [ ] Every parameter change, rule change, and variant tested during
      training for this `strategy_version` has a row in
      `docs/research_contamination_log/research_contamination_log.csv`
      whose `dataset_used=training` and whose `datetime_iso` precedes
      this freeze.
- [ ] No source-tree change to a strategy parameter file lacks a
      corresponding contamination-log row (cross-reference `git log` for
      the strategy module against the log).
- [ ] `validate_log("docs/research_contamination_log/research_contamination_log.csv")`
      (`src/algotrading/contamination/log.py:142`) returns an empty list.

**Falsifier:** any uncovered training-period code change, any schema
error from `validate_log`.

## 3. Data-partition lock is signed

- [ ] `configs/data_partitions.yml` has `locked: true`.
- [ ] `signed_by` and `locked_at_iso` are non-empty.
- [ ] `partitions.training.start`, `.training.end`, `.validation.start`,
      `.validation.end`, `.final_holdback.start`, `.final_holdback.end`
      are all non-empty.
- [ ] `is_partition_lock_signed("configs/data_partitions.yml")`
      (`src/algotrading/contamination/enforcement.py:32`) returns
      `True`.

**Falsifier:** any of the above fields empty or `locked: false`.

## 4. Risk-limits lock is signed

- [ ] `configs/risk_limits.yml` has `locked: true`.
- [ ] `signed_by` (Director Sponsor identifier) and `signed_at_iso` are
      non-empty.
- [ ] All numeric fields (`allocated_capital_usd`,
      `max_oos_drawdown_pct`, `max_acceptable_losing_streak`,
      `daily_loss_limit_usd`, `aggregate_program_drawdown_limit_pct`,
      `risk_of_ruin_threshold_pct`) are populated and within the bounds
      stated in the file's preamble (`configs/risk_limits.yml:7-12`).
- [ ] The `signed_by` identifier on `configs/risk_limits.yml` is **not**
      the same identifier as the Risk Reviewer (per `docs/OWNERS.md`
      independence rule, lines 18-23).

**Falsifier:** any unset numeric, `locked: false`, missing signer, or
identifier overlap with the Risk Reviewer.

## 5. Pre-code sign-off matrix complete

- [ ] In `configs/signoff_matrix.yml`, all five pre-code rows are
      marked `signed: true` with non-empty `signed_by` and
      `signed_at_iso`:
  - [ ] Row `B` — Appendix B (Director Sponsor)
  - [ ] Row `C` — Appendix C (Risk Reviewer)
  - [ ] Row `D` — Appendix D (Engineering)
  - [ ] Row `E` — Appendix E (Quant)
  - [ ] Row `H` — Appendix H (Engineering)
- [ ] Each `signed_at_iso` is strictly earlier than this freeze's
      proposed `datetime_iso`.
- [ ] No row's `signed_by` matches the Risk Reviewer identifier on rows
      whose `signer_role` is not `Risk reviewer`.

**Falsifier:** any pre-code row with `signed: false`, any role mismatch,
or any signature dated after this freeze.

## 6. Broker rate sheet has replaced D2_PLACEHOLDER

- [ ] The strategy's planned backtest config does not contain the token
      `D2_PLACEHOLDER` anywhere (per errata §5,
      `docs/v1.4r1_errata_and_kickoff.md:43`; see also
      `docs/GATES.md:33-35` — CI fails if the marker survives).
- [ ] Row `broker_rate_sheet` in `configs/signoff_matrix.yml` is
      `signed: true` with Ops `signed_by` set.
- [ ] The fee, commission, and slippage values in the backtest config
      match the broker rate sheet referenced from Appendix D and
      Appendix F. Cross-check the rate sheet hash recorded in the
      registry entry's `note`.

**Falsifier:** any surviving `D2_PLACEHOLDER`, unsigned
`broker_rate_sheet` row, or value mismatch with the rate sheet. Errata
§5 forbids placeholder costs in any approved backtest output, and the
OOS pass/fail evaluation is a research-report-quality run.

## 7. Validation_freeze row appended to contamination log

- [ ] A row exists in
      `docs/research_contamination_log/research_contamination_log.csv`
      with:
  - `strategy_version` = the version being frozen,
  - `action_type` = `other`,
  - `description` containing the substring `validation_freeze`
    (case-insensitive — see
    `src/algotrading/contamination/enforcement.py:69-75`),
  - `dataset_used` = `none`,
  - `decision` = `kept`.
- [ ] The row's `datetime_iso` is the moment this checklist is signed
      (or earlier — never later).
- [ ] The row's `researcher` matches the Risk Reviewer identifier on
      `configs/signoff_matrix.yml` row `validation_freeze`.
- [ ] `enforce_no_validation_before_freeze(strategy_version=...,
      partitions_path="configs/data_partitions.yml",
      contamination_log_path="docs/research_contamination_log/research_contamination_log.csv")`
      (`src/algotrading/contamination/enforcement.py:51`) returns
      without raising.

**Falsifier:** absence of the freeze row, a freeze row whose timestamp
post-dates partition reads, or the enforcement guard raising.

## 8. One-shot OOS rule

- [ ] No row in the contamination log for this `strategy_version` has
      `dataset_used=validation`. (After the freeze is signed, the
      one-and-only OOS query may be run; before the freeze, the count
      must be zero.)
- [ ] No row in the contamination log for any **prior** version in the
      same family has been re-used as a validation query for this
      version. Inheriting OOS data from a prior version is governed by
      §B.13 (errata §6) and requires the registry-first check in §1
      above.

Reviewer command (POSIX):

```
awk -F, -v v="<strategy_version>" '$3==v && $6=="validation"' \
  docs/research_contamination_log/research_contamination_log.csv
```

Expected output: empty.

**Falsifier:** any prior `dataset_used=validation` row for this
version, or any cross-version OOS reuse without a prior registry
entry.

---

## Contamination-log row template — validation freeze

When all eight checks pass, the Risk Reviewer appends exactly one row
to the contamination log to mark the freeze. Use the literal template
below, substituting the bracketed fields. Do **not** alter the column
order. RFC-4180 quote any field containing a comma, quote, or newline
(`docs/research_contamination_log/README.md:46-53`).

Header (for reference, must already be the first line of the file):

```
datetime_iso,researcher,strategy_version,action_type,description,dataset_used,result_observed,decision,reviewer_initials,reviewer_date
```

Freeze row template:

```
<ISO-8601 with offset>,<risk_reviewer_id>,<strategy_version>,other,"validation_freeze: partition lock configs/data_partitions.yml signed at <locked_at_iso> by <locked_by>; signoff_matrix rows B,C,D,E,H signed; broker rate sheet substituted; registry entry_id <registry_entry_id> rules_hash <rules_hash>; one-shot OOS authorised for <strategy_version>",none,N/A,kept,<risk_reviewer_initials>,<YYYY-MM-DD>
```

After this row is committed, the validation harness will permit
exactly one OOS query for `<strategy_version>`. A second query against
the same partition for the same version is a contamination event and
falls under the Decline conditions in
`docs/risk/contamination_review_checklist.md`.
