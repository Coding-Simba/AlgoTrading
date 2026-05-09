# Contamination review checklist

**Owner:** Risk Reviewer (independent — see `docs/OWNERS.md`)
**When used:** Every gate review (pre-code sign-off, approved-backtest, OOS,
final-holdback, paper, small-size live, scale-up).
**Status of file:** Authoritative. Sign-off rows in
`configs/signoff_matrix.yml` may not be marked signed unless every check
below resolves to PASS or N/A with documented justification.

This checklist is read alongside the Research Contamination Log
(`docs/research_contamination_log/README.md`) and the Sprint 1 freeze guard
(`tests/test_sprint1_freeze.py`). Each item is falsifiable: the reviewer
records PASS / FAIL / N/A and a short evidence pointer (file path + line, or
shell command output). Vague affirmations ("looks good") are not acceptable.

---

## 1. Log existence and header

- [ ] The file `docs/research_contamination_log/research_contamination_log.csv`
      exists and is non-empty.
- [ ] The first line of the file is exactly the canonical header:
      `datetime_iso,researcher,strategy_version,action_type,description,dataset_used,result_observed,decision,reviewer_initials,reviewer_date`
      (see `src/algotrading/contamination/log.py:35` — `HEADER` tuple).

**Falsifier:** `head -n 1 docs/research_contamination_log/research_contamination_log.csv`
must match the header line above byte-for-byte.

## 2. Schema validation passes

- [ ] Running `validate_log("docs/research_contamination_log/research_contamination_log.csv")`
      from `src/algotrading/contamination/log.py:142` returns an empty list.
- [ ] All `action_type` values are in
      `{parameter_change, rule_change, variant_tested, validation_query, data_qa_check, other}`
      (`log.py:21`).
- [ ] All `dataset_used` values are in
      `{training, validation, live, paper, none}` (`log.py:30`).
- [ ] All `decision` values are in
      `{kept, discarded, logged_for_next_version, escalated}` (`log.py:32`).
- [ ] Every row has a non-empty `researcher` and `strategy_version`
      (`log.py:73-76`).
- [ ] Every `datetime_iso` parses via `datetime.fromisoformat` with timezone
      offset (`log.py:77-80`).

**Falsifier:** any returned error string from `validate_log`.

## 3. No validation queries before freeze

- [ ] For each `strategy_version` present in the log, there is a row with
      `action_type=other` whose description contains `validation_freeze`
      (case-insensitive — see
      `src/algotrading/contamination/enforcement.py:69-75`).
- [ ] No row with `dataset_used=validation` for that `strategy_version` has
      a `datetime_iso` earlier than the corresponding `validation_freeze`
      row's `datetime_iso`.
- [ ] The partition lock (`configs/data_partitions.yml`) was already signed
      at the time of the freeze row (`enforcement.py:32-48` —
      `is_partition_lock_signed`).

**Falsifier:** any `dataset_used=validation` row whose timestamp precedes
the version's `validation_freeze` row, or absence of the freeze row.

## 4. Live / paper datasets only after gate sign-off

- [ ] No row has `dataset_used=paper` unless the `F` (Appendix F
      finalized) row in `configs/signoff_matrix.yml` is signed
      (signed=true, signed_by and signed_at_iso non-empty), with
      `signed_at_iso` earlier than the row's `datetime_iso`. Appendix I
      is a scope-control note for internal-only scope and is not part
      of the paper-gate set; if a scope-expansion trigger fires (client
      / outside / pooled capital, paid signals, paid advice,
      copy-trading, public marketing, managed accounts), the paper /
      live dataset is additionally gated on Appendix I review.
- [ ] No row has `dataset_used=live` unless the `paper` row in
      `configs/signoff_matrix.yml` is signed earlier than the row's
      `datetime_iso`.

**Falsifier:** any premature `paper` or `live` dataset row.

## 5. Append-only invariant

- [ ] `git log --follow docs/research_contamination_log/research_contamination_log.csv`
      shows only commits whose diff is **append** (no removed lines except
      for trailing-newline normalization).
- [ ] Any correction is a NEW row whose `description` references the
      original row's `datetime_iso` and `researcher`
      (see `docs/research_contamination_log/README.md` — "Append-only rule",
      lines 20-30).
- [ ] No row's `reviewer_initials` / `reviewer_date` has been edited after
      first being filled — corrections instead append a new row with
      `decision=escalated`.

**Falsifier:** any commit diff that removes or modifies an existing data row.

## 6. Sprint 1 freeze: no forbidden strategy code

- [ ] `pytest tests/test_sprint1_freeze.py` passes (see
      `tests/test_sprint1_freeze.py:22-30` for the forbidden patterns:
      `V0_?2*Strategy`, `v0_?2_*signal`, `b_?7_entry`, `b_?8_entry`,
      `compute_ema_signal`, `compute_vwap_signal`, `compute_atr_signal`).
- [ ] No directories `src/algotrading/strategies/`, `src/algotrading/signals/`,
      or `src/algotrading/indicators/` exist (these are forbidden under
      Sprint 1 scope per `docs/v1.4r1_errata_and_kickoff.md` §9).
- [ ] `src/algotrading/baselines/` does not import or reference `ema`,
      `vwap`, or `atr` (see `tests/test_sprint1_freeze.py:47-54`).

**Falsifier:** any failing pattern in `test_sprint1_freeze.py`, or the
presence of any of the three forbidden directories before the pre-code
sign-off matrix is fully signed.

## 7. No chart screenshots committed

- [ ] `find . -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg'
      -o -iname '*.webp' -o -iname '*.gif' -o -iname '*.bmp' \)` returns
      zero results under the repo root (excluding `.git/`).
- [ ] No commit message in the current branch references "chart",
      "screenshot", or "plot" attached as binary content.

**Falsifier:** any image file present anywhere in the working tree. Charts
are evidence of visual curve-fitting and are not a permitted research
artefact at any phase.

## 8. Registry / contamination-log cross-reference

- [ ] Every `strategy_version` appearing in the contamination log has at
      least one corresponding entry in the strategy registry
      (`src/algotrading/registry/registry.py` — see `latest_for_version`
      at line 98 and `iter_versions` at line 182).
- [ ] Every variant referenced via `action_type=variant_tested` has either
      (a) a registry entry whose `strategy_version` matches, or
      (b) a `decision=discarded` outcome with a description naming the rule
      change. There are no undocumented variants.
- [ ] `StrategyRegistry.validate()` (`registry.py:161`) returns an empty
      list.

**Falsifier:** any `strategy_version` in the log not present in the
registry, or any registry entry with no corresponding contamination-log
row at or before its `registered_at`.

## 9. No strategy code before pre-code sign-off matrix complete

- [ ] If any of the rows `B`, `C`, `D`, `E`, `H` in
      `configs/signoff_matrix.yml` has `signed: false`, then no strategy
      module exists in `src/algotrading/` other than framework modules
      (`bars`, `baselines`, `calendar`, `contamination`, `fillmodel`,
      `governance`, `ingestion`, `monitoring`, `orders`, `registry`).
- [ ] When the matrix is complete, the addition of any strategy module is
      accompanied by a registry append and a contamination-log row in the
      same commit.

**Falsifier:** any strategy implementation file landed while a pre-code
row is unsigned.

## 10. Risk Reviewer independence

- [ ] The reviewer signing this checklist (recorded in `reviewer_initials`
      on the contamination log and in `signed_by` on the relevant
      `configs/signoff_matrix.yml` row) is **not** the same individual
      listed under Engineering, Quant, or Director Sponsor in
      `docs/OWNERS.md` for this strategy family.
- [ ] The reviewer signature on `configs/risk_limits.yml` (`signed_by`)
      and on the contamination log are **distinct** identifiers — risk
      limits are signed by the Director Sponsor; contamination is signed
      by the Risk Reviewer (`docs/OWNERS.md` lines 18-23).

**Falsifier:** identifier overlap between the contamination reviewer and
any of {Engineering owner, Quant owner, Director Sponsor} on the same
family.

---

## Decline conditions

A finding in any one of the following bullets results in **automatic
strategy rejection**. The Risk Reviewer does not continue the review and
does not sign the gate.

1. **Validation peek.** A `dataset_used=validation` row exists with a
   `datetime_iso` earlier than the corresponding `validation_freeze` row
   for the same `strategy_version`, or the freeze row is missing.
2. **Premature paper / live.** A `dataset_used=paper` or
   `dataset_used=live` row exists before the corresponding sign-off row in
   `configs/signoff_matrix.yml` was signed.
3. **In-place edit.** Any historical row of
   `research_contamination_log.csv` has been modified or removed (git
   history shows non-append diff).
4. **Schema corruption.** `validate_log` returns any errors and the
   errors are not corrected via a new appended row before the gate.
5. **Forbidden code at Sprint 1.** `tests/test_sprint1_freeze.py` fails,
   or `src/algotrading/strategies/`, `src/algotrading/signals/`, or
   `src/algotrading/indicators/` exists while Sprint 1 is in force.
6. **Image artefacts.** Any `*.png`, `*.jpg`, `*.jpeg`, `*.webp`, `*.gif`,
   or `*.bmp` is committed to the repository.
7. **Registry / log mismatch.** A `strategy_version` is referenced in the
   contamination log without a corresponding registry entry, or a
   registry entry exists whose rules cannot be matched to a
   contamination-log row.
8. **Independence breach.** The reviewer signing this checklist also
   appears as the Engineering, Quant, or Director Sponsor on the same
   family in `docs/OWNERS.md`.
9. **Undisclosed exploration.** Variants found in the registry, in code,
   or in research notes that have no contamination-log row
   (`docs/research_contamination_log/README.md` — "Logs that show
   validation queries before the documented Week 3 freeze step are
   evidence of contamination and result in strategy rejection").

A rejected strategy may only re-enter the pipeline as a **new
`strategy_version` with a new registry entry** per §B.13 — see
`docs/risk/gate_failure_protocol.md` "Re-entry".
