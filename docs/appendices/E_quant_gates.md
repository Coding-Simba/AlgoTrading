# Appendix E — Quantitative Gates (sign-off template)

**Status:** Pre-code sign-off. Empty until signed; signed copies are committed
via PR.
**Frozen by:** errata §3 (pre-code sign-off rows are FROZEN).
**Cost gating:** placeholder costs (`D2_PLACEHOLDER`) **may not** appear in
any output to which an E-gate threshold is applied (errata §5; Appendix D).

---

## 1. Scope of this sign-off

This appendix signs the **quantitative gate METHODOLOGY** at the
specification level — not the Director-set numeric values. The numeric
values (capital, drawdown ceilings, daily loss limit, losing-streak
ceiling, ROR threshold) live in `configs/risk_limits.yml` and are
signed **separately** by the Director Sponsor at the risk-limits gate.
A methodology-only signature on this appendix does not by itself
unblock v0.2 strategy code; the risk-limits gate must also pass.

Once signed, the following are binding inputs to v0.2 strategy work
and may not be edited without a Change Request:

- Per-strategy quantitative thresholds: expectancy floor (in R), Sharpe
  floor, maximum drawdown ceiling, win-rate floor, trade-count floor.
- Baseline-must-beat rules: each of the four required baselines (random,
  drift-matched random, reversed-signal, session-exposure) defines a
  hurdle on the same metrics; a candidate must beat all four on the
  training partition before any validation query is permitted.
- Validation / OOS gating: one-shot OOS test per strategy version, gated
  by the partition lock (Appendix C) and the validation-freeze
  contamination event.
- Final-holdback gating: family-level binding test, run after the
  per-strategy OOS pass and after the holdback partition trade-count
  threshold is met.

Numeric Director-set values (capital, drawdown, daily loss limit, losing
streak, aggregate program drawdown, risk-of-ruin ceiling) live in
`configs/risk_limits.yml`. This appendix signs the **rules** that apply
those values; the values themselves are signed by the Director Sponsor in
the risk-limits file.

## 2. What this sign-off unblocks

Per `docs/GATES.md`:

- The `v0.2 strategy code` gate (jointly with B, C, D, H).
- Following sign-off and validation freeze (Week 3), the
  `Validation / OOS query` gate may run **one** OOS test per strategy
  version against the validation partition.
- After OOS pass and once the holdback partition trade-count threshold is
  met, the `Family final-holdback query` gate may run.

This sign-off does **not** unblock approved v0.2 backtests. That gate
requires the broker rate sheet to replace `D2_PLACEHOLDER` costs (errata
§5; Appendix D). Any pass / fail evaluation against E thresholds run on
placeholder-cost output is invalid by construction.

## 3. Dependencies on other appendices

- **Appendix B**: defines the rule set whose performance is being
  measured. E presupposes B is signed.
- **Appendix C**: defines the partitions on which training, validation,
  and final-holdback metrics are computed. E presupposes C is on track to
  be signed and the partition lock file is populated.
- **Appendix D**: provides the cost model. E thresholds are meaningless
  on placeholder-cost output. The reviewer confirms every E threshold
  refers to a fill stream where `FillResult.is_placeholder() == False`.
- **Appendix H**: forced-flatten and kill-switch behaviour affect realised
  drawdown. E drawdown thresholds presume H rules are in force.
- **`configs/risk_limits.yml`**: Director-set numeric values. E rules
  consume these; they are not redefined here.

## 4. Source modules and tests referenced

- `src/algotrading/baselines/runners.py` — `RandomBaseline`,
  `DriftMatchedRandom`, `ReversedSignalBaseline`,
  `SessionExposureBaseline`. Signal contract: `-1 | 0 | +1` per bar.
- `src/algotrading/contamination/enforcement.py` —
  `enforce_no_validation_before_freeze`. Refuses validation queries
  unless the partition lock is signed and a `validation_freeze` event
  is logged for the strategy version.
- `src/algotrading/contamination/log.py` — `ContaminationLog`,
  append-only, used to record validation queries.
- `configs/risk_limits.yml` — Director-set risk values.
- `configs/data_partitions.yml` — partition lock (Appendix C).
- `tests/test_baselines.py`, `tests/test_contamination.py`.

## 5. Review checklist

The signer must verify each item below by direct inspection. Initial each
box. Unchecked items block the signature.

1. [ ] Each per-strategy threshold is written as a single number with
       units and a comparison direction (`>=`, `<=`). At minimum:
       expectancy floor (R per trade), Sharpe floor (annualised),
       maximum drawdown ceiling (% of allocated capital), win-rate floor
       (%), trade-count floor (count over the partition). No threshold
       is "to be calibrated."
2. [ ] Each threshold cites the partition it applies to. Training,
       validation, and final-holdback may use different floors, but each
       must be named explicitly.
3. [ ] All four baselines are required hurdles, not optional: random,
       drift-matched random, reversed-signal, session-exposure. The
       candidate must beat all four on the training partition before any
       validation query is run. The reviewer has confirmed each of the
       four runner classes exists in `baselines/runners.py`.
4. [ ] The drift-matched random baseline uses the **training-period**
       drift only. The reviewer has confirmed there is no path that
       computes drift over the validation or final-holdback partition.
5. [ ] The reversed-signal baseline is constructed from the **candidate
       strategy's own signal stream** at the same parameter point being
       tested. A reversed-signal hurdle that loses to its inverse is a
       fail.
6. [ ] The session-exposure baseline uses the same `SessionCalendar` the
       candidate uses; the reviewer has confirmed a single calendar
       object is shared, not two independently configured copies.
7. [ ] Validation / OOS gating is **one-shot per strategy version**. A
       second query against the same partition for the same version is
       a contamination event and is recorded in the contamination log.
       The reviewer has read the rule wording and confirmed there is no
       "retry" or "re-run" carve-out.
8. [ ] The validation partition cannot be opened until
       `enforce_no_validation_before_freeze` succeeds: partition lock
       signed AND a `validation_freeze` event logged for the strategy
       version. The reviewer has read the enforcement source and
       confirmed there is no override flag.
9. [ ] Final-holdback gating requires (a) OOS pass for the strategy
       version, (b) holdback partition trade-count threshold met, (c)
       the holdback query is run **once** at family level. The
       reviewer has confirmed the trade-count threshold is the value
       written in §5 item 1, not a different number.
10. [ ] Director-set risk values (`configs/risk_limits.yml`) are filled
        and `locked: true` at the time of signing. The reviewer has
        confirmed `signed_by` and `signed_at_iso` are populated and
        `signed_by` differs from the Risk Reviewer identifier
        (independence rule).
11. [ ] Every E-gate evaluation is run against a fill stream whose
        `FillResult.is_placeholder()` is `False` for all rows. The
        reviewer has confirmed CI fails any evaluation report that
        carries the literal `D2_PLACEHOLDER` (Appendix D §5 item 9;
        errata §5).
12. [ ] §B.13 alignment: any v0.3 attempt to use the v0.2 OOS partition
        as clean validation requires that v0.3 rules be appended to the
        `StrategyRegistry` **before** the v0.2 OOS query was run
        (errata §6). The reviewer has confirmed E does not contain
        wording that contradicts §B.13.
13. [ ] No threshold in this appendix is computed from the validation
        or final-holdback partitions. All calibration is on training
        only; validation and final-holdback are read-once gate
        partitions.
14. [ ] The contamination log workflow is acknowledged: each baseline
        run on training is logged once at the strategy-version level
        (per `docs/research_contamination_log/README.md`); each
        validation or final-holdback query is logged per query.

## 6. Sign-off block

Empty by default. To sign, fill the row, commit on a branch, and open a PR
labelled `signoff-appendix-e`. Per `configs/signoff_matrix.yml`, the
required `signer_role` is **Quant**. The Risk Reviewer must independently
acknowledge the PR (independence rule, `docs/OWNERS.md`).

| Field           | Value |
| --------------- | ----- |
| Signer name     |       |
| Role            |       |
| Date (ISO-8601) |       |
| Notes           |       |

Allowed roles for this appendix (per `docs/OWNERS.md` and
`configs/signoff_matrix.yml`):

- Quant — baselines + validation harness (primary).
- Director sponsor — risk values referenced from
  `configs/risk_limits.yml` (signed there, not here).
- Risk reviewer (independence ack on the PR; not a co-signer).
