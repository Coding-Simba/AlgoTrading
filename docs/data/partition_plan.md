# Partition Plan (DRAFT)

**Status:** Draft. Not a lock. Not a Change Request.
**Applies to:** `configs/data_partitions.draft.yml`. Production lock file
(`configs/data_partitions.yml`) is unchanged by this document.
**Issued:** 2026-05-09
**Owner:** Strategy Owner (Director Sponsor signs the production lock).

---

## 1. Purpose

This document accompanies `configs/data_partitions.draft.yml` and explains
the candidate training / validation / final-holdback ranges proposed there.
It is a planning artefact for Phase 1 review; it does not authorise any
query against validation or holdback data and does not load any market
data. The production lock file remains untouched.

The draft proposes:

| Partition       | Start        | End          |
| --------------- | ------------ | ------------ |
| training        | 2019-05-06   | 2024-12-31   |
| validation      | 2025-01-02   | 2025-12-31   |
| final_holdback  | 2026-01-02   | 2026-04-30   |

Each row carries `candidate_only: true` in the draft and is subject to
revision before the Director Sponsor signs the production lock.

## 2. Why these ranges

- **Training begins on 2019-05-06.** This is the MES launch date. No
  pre-launch window is proposed; pre-launch work would require the ES-proxy
  rule in §4.
- **Training ends on 2024-12-31.** A clean year boundary separates training
  from validation. The width (~5.7 years) provides multiple market regimes
  while leaving a full year for one-shot OOS.
- **Validation is the full calendar year 2025.** A single calendar year is
  the smallest unit that produces a recognisable cross-regime sample for
  the §B.13 / §E one-shot OOS query. Per §B.13 (canonical, errata §6), the
  validation partition is clean for v0.3 only if v0.3 is appended to
  `StrategyRegistry` before the v0.2 OOS query runs against this range.
- **Final holdback is 2026-01-02 to 2026-04-30.** Family-level binding
  test; deliberately narrow so that training is not starved. The Director
  Sponsor sets the binding width.

These ranges are proposals. Reviewer comments are welcome.

## 3. What this plan protects

- **§C.9 partition-lock invariant.** The contamination guard
  (`src/algotrading/contamination/enforcement.py::enforce_no_validation_before_freeze`)
  is functionally inert until the production lock file is populated and
  signed. This draft does not satisfy that condition; it merely proposes
  the values.
- **§B.13 registry-first rule (canonical per errata §6).** If v0.3 is
  designed in response to v0.2 OOS results — even casually — and is not
  registered in `StrategyRegistry` before the v0.2 OOS query, the
  validation partition is permanently contaminated for v0.3 and may serve
  only as a diagnostic comparison, never as a clean pass/fail gate. The
  final holdback remains binding family-level validation regardless.
- **One-shot rule (§E).** A second query against the validation partition
  for the same strategy version is a contamination event recorded in
  `docs/research_contamination_log/research_contamination_log.csv`.

## 4. MES history limitation

MES launched on **2019-05-06**. Any backtest window prior to that date
cannot be sourced from MES; if pre-launch coverage is needed, the ES-proxy
rule (§5) applies. The draft does not propose any pre-launch window.

The five-year-and-change MES history is a soft constraint on training
width. If a future review concludes more training history is required, the
options are:

1. Move the training start later (less data, no proxy required).
2. Splice ES history before 2019-05-06 under the ES-proxy rule with the
   contamination disclosure block (§5).
3. Narrow validation or holdback (only with Director Sponsor sign-off; a
   narrow holdback is preferable to splicing pre-launch ES into training
   because the contamination implications are smaller).

## 5. ES-proxy rule

When permitted at all, an ES-proxy splice is allowed only under all of the
following conditions:

- The proxy window is strictly before 2019-05-06.
- The strategy spec being tested is not contract-microstructure-sensitive
  in a way that ES-vs-MES differences would materially affect the result
  (tick size, multiplier, margin, BBO depth). The Risk Reviewer signs off
  on this independence claim by direct inspection.
- The research report carries an explicit ES-proxy disclosure block
  stating: (a) the proxy window, (b) the splice convention, (c) the
  contract-multiplier conversion used, (d) the known differences in tick
  size and depth, and (e) the resulting contamination implications.
- The contamination log records a `data_qa_check` row with
  `dataset_used = training` referencing the splice.

**Contamination implications.** An ES-spliced training run is no longer
"MES on training partition." It is a hybrid. Any v0.2 metric computed on
such a run must carry the proxy disclosure when reported. A v0.3
constructed in response to such a metric inherits the disclosure.

The current draft `es_proxy_required: false` and proposes no proxy
splice.

## 6. No overlap

Non-overlap is defined as:

- `training.end < validation.start` strictly. Comparison is by ISO date.
- `validation.end < final_holdback.start` strictly.
- No calendar date appears in more than one partition. Half-days,
  holidays, and overnight session boundaries are reconciled by the
  session calendar (`configs/sessions/mes.yml`); a date that contains
  even a single bar belonging to a partition counts as a date for that
  partition.

**Verification procedure.**

1. Reviewer reads `configs/data_partitions.draft.yml`.
2. Reviewer asserts `training.end < validation.start` and
   `validation.end < final_holdback.start` by ISO comparison.
3. Reviewer cross-references each boundary date against the signed
   session calendar to confirm that no half-day or holiday spans two
   partitions.
4. Reviewer flips `no_overlap_verified` to `true` in the draft (this is
   the only field a reviewer may flip without Director Sponsor
   countersignature).

The current draft sets `no_overlap_verified: false` until step 4 is
performed.

## 7. Final-holdback trade-count requirement

The final holdback partition is binding family-level validation only when
the trade-count floor specified by Appendix E §5 is met. The draft
proposes a candidate value of `final_holdback_min_trades: 50`. This
number is illustrative and not a Director Sponsor commitment.

The Director Sponsor sets the binding number at the same time as signing
the production lock file. Until then, the candidate value is for review
discussion only. A holdback partition that fails to reach the trade-count
floor cannot be used as a binding family-level test; it may serve as a
diagnostic comparison, with the diagnostic status disclosed.

## 8. What this draft does NOT do

- Does **not** query the validation partition.
- Does **not** query the final-holdback partition.
- Does **not** load any market data, tick or BBO, primary or secondary.
- Does **not** unlock, modify, or replace the production lock file at
  `configs/data_partitions.yml`.
- Does **not** countersign on behalf of the Director Sponsor.
- Does **not** authorise any v0.2 backtest or any v0.2 baseline run.
- Does **not** bind any future v0.3 to the registry-first rule by
  itself; that rule is binding via §B.13 regardless of this draft.

## 9. Promotion path

The draft is promoted to the production lock file by the following
sequence (all post-Phase-1):

1. Phase 1 review of this draft and `data_qa_acceptance_checklist.md`
   completes; reviewer comments are addressed in this draft.
2. Director Sponsor sets binding values (date ranges,
   `final_holdback_min_trades`).
3. The production file `configs/data_partitions.yml` is edited in a
   single PR that also signs Appendix C (independence rule:
   `docs/OWNERS.md`); `locked` is flipped to `true`, `locked_by` and
   `locked_at_iso` are populated.
4. The contamination guard is now operative.
5. This draft remains in-tree as a historical artefact and is not
   re-edited after promotion.
