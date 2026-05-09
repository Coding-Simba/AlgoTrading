# Appendix C — Data QA & Partitioning (sign-off template)

**Status:** Pre-code sign-off. Empty until signed; signed copies are committed
via PR.
**Frozen by:** errata §3 (pre-code sign-off rows are FROZEN).
**Canonical rule reference:** §C.9 wording defers to §B.13 on any
inconsistency. The registry-first rule of §B.13 is canonical for OOS /
holdback questions (errata §6).

---

## 1. Scope of this sign-off

This appendix signs the **data-QA and partitioning PROCESS** at the
specification level — not the actual numeric date ranges. The numeric
ranges live in `configs/data_partitions.yml` and are signed
**separately** by the Director Sponsor at the partition-lock gate. A
process-only signature on this appendix does not by itself unblock v0.2
strategy code; the partition-lock gate must also pass.

Once signed, the following are binding inputs to v0.2 strategy work and
may not be edited without a Change Request:

- Vendor selection criteria for primary and secondary historical data
  sources (MES tick + BBO).
- Gap policy: how missing ticks, missing bars, and feed outages are detected
  and recorded.
- Corporate-action handling (contract roll convention, expiry handling,
  symbol changes).
- Cross-vendor reconciliation rules: sample windows, tolerance bands, and
  the decision rule when primary and secondary disagree.
- Decision rules for QA failures: which conditions reject a partition row,
  which trigger a re-pull, which escalate.
- The locked **training**, **validation**, and **final\_holdback** date
  ranges in `configs/data_partitions.yml`.

The actual ranges are signed by the Director Sponsor at the partition lock
step (`docs/PROCUREMENT.md` — internal lock, Day 0). This appendix signs the
**rules** governing those ranges and the QA process around them.

## 2. What this sign-off unblocks

Per `docs/GATES.md`:

- The `v0.2 strategy code` gate (jointly with B, D, E, H).
- The contamination guard
  (`src/algotrading/contamination/enforcement.py::enforce_no_validation_before_freeze`)
  is functionally inert until `configs/data_partitions.yml` is locked. Signing
  this appendix is a precondition for the partition lock to be considered
  binding policy, not just a YAML file.

This sign-off does **not** unblock approved v0.2 backtests. That gate
additionally requires the broker rate sheet (errata §5) and a primary +
secondary vendor reply on file (`docs/PROCUREMENT.md`).

## 3. Dependencies on other appendices

- **Appendix B**: §B.13 is the canonical rule when §C.9 wording appears to
  conflict (errata §6). The reviewer must confirm this appendix does not
  re-state §C.9 in a way that contradicts §B.13.
- **Appendix E**: validation / OOS gating in E presumes a locked partition
  file. E cannot be signed before C is on track to be signed.
- **Procurement**: the partition-lock row in `docs/PROCUREMENT.md` is the
  operational counterpart of this appendix. The internal lock is sent
  Day 0 and recorded in the procurement tracking table.

## 4. Source modules and tests referenced

- `configs/data_partitions.yml` — the lock file. Edits after sign-off
  require a Change Request.
- `src/algotrading/contamination/enforcement.py` —
  `is_partition_lock_signed`, `enforce_no_validation_before_freeze`.
- `src/algotrading/contamination/log.py` — append-only contamination log
  used for `validation_freeze` events.
- `src/algotrading/ingestion/parser.py` — tick / BBO parser (rejects
  malformed and crossed-book-with-size rows).
- `src/algotrading/ingestion/pipeline.py` — multi-source merge by
  timestamp, used for cross-vendor reconciliation.
- `tests/test_ingestion.py`, `tests/test_contamination.py`.
- `docs/research_contamination_log/README.md` — log conventions.

## 5. Review checklist

The signer must verify each item below by direct inspection. Initial each
box. Unchecked items block the signature.

1. [ ] Primary vendor selection criteria are written down: history depth,
       tick + BBO availability, gap-disclosure policy, corporate-action
       handling, revisions policy. The criteria are objective enough that a
       different reviewer could apply them and reach the same shortlist.
2. [ ] Secondary vendor selection criteria are written down and require
       independence from the primary's upstream feed where possible.
       `docs/PROCUREMENT.md` lists this requirement; this appendix must
       not relax it.
3. [ ] Gap policy specifies, for each data class (tick, BBO, bar),
       (a) the detection rule (e.g., interval > expected by N ticks /
       seconds), (b) the recording location (filename, log row), and
       (c) the downstream effect (drop, flag, re-pull).
4. [ ] Corporate-action handling specifies the contract-roll convention
       (calendar vs volume), how the rolled series is stitched, and how
       the contamination log records each roll-related correction.
5. [ ] Cross-vendor reconciliation specifies a sample window (size,
       cadence), a tolerance band per field (price, volume, BBO), and a
       decision rule when primary and secondary disagree beyond tolerance.
       The decision rule names a single owner.
6. [ ] QA failure decision rules enumerate each failure class (gap,
       cross-vendor mismatch, missing corporate action, parser reject)
       and map each to one of: drop row, flag row, re-pull, escalate. No
       failure class is unmapped.
7. [ ] `configs/data_partitions.yml` schema is acknowledged: `locked`,
       `locked_by`, `locked_at_iso`, and the three partition `start` /
       `end` fields. The reviewer has confirmed
       `is_partition_lock_signed` returns `False` until all six required
       fields are populated.
8. [ ] Training, validation, and final\_holdback date ranges are
       non-overlapping, monotonically ordered (training < validation <
       final\_holdback), and each range is wide enough to satisfy the
       trade-count floor in Appendix E §5.
9. [ ] The validation partition is named in the spec exactly once; the
       spec contains no worked examples, summary statistics, or QA
       outputs derived from the validation or final\_holdback ranges.
10. [ ] The contamination log workflow is acknowledged: every QA
        correction that rewrites training or validation rows is logged
        per `docs/research_contamination_log/README.md` field
        definitions. The reviewer has confirmed there is no override
        path that would suppress a log row.
11. [ ] The §C.9 wording in this appendix defers to §B.13 in writing;
        any v0.3 OOS / holdback claim is governed by the registry-first
        rule (errata §6), not by C.9 wording.
12. [ ] No row of the data partition lock contains a placeholder string
        (`""`, `"TBD"`, `"YYYY-MM-DD"`) at the moment this appendix is
        signed. If the lock is to be signed in the same PR, both files
        appear in the same commit.
13. [ ] The Director Sponsor has separately countersigned
        `configs/data_partitions.yml` (per `docs/OWNERS.md`); the Risk
        Reviewer signing this appendix is a different individual than
        the Director Sponsor (independence rule).

## 6. Sign-off block

Empty by default. To sign, fill the row, commit on a branch, and open a PR
labelled `signoff-appendix-c`. Per `configs/signoff_matrix.yml`, the
required `signer_role` is **Risk reviewer**. The Director Sponsor's
countersignature on `configs/data_partitions.yml` is a separate artefact in
the same PR (independence rule, `docs/OWNERS.md`).

| Field           | Value |
| --------------- | ----- |
| Signer name     |       |
| Role            |       |
| Date (ISO-8601) |       |
| Notes           |       |

Allowed roles for this appendix (per `docs/OWNERS.md` and
`configs/signoff_matrix.yml`):

- Risk reviewer — contamination log + sign-off gate (primary; this
  appendix governs the partitions over which contamination is defined).
- Director sponsor — partition date-range values (signed in the
  partition-lock file, not on this row).
- Engineering — ack only (data layer implementation), not a co-signer.
