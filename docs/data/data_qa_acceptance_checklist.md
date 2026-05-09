# Data QA Acceptance Checklist (DRAFT — reviewer-facing)

**Status:** Draft. Reviewer-facing checklist used in Phase 1 review of the
partition draft (`configs/data_partitions.draft.yml`) and the vendor replies
on file. Not a sign-off gate by itself; this checklist supports the Risk
Reviewer's signature on Appendix C and the Director Sponsor's
countersignature on `configs/data_partitions.yml`.
**Issued:** 2026-05-09
**Owner:** Risk Reviewer (with Ops as data-source counterparty).

---

## 0. How to use this checklist

Each item below is concrete and falsifiable. The reviewer marks each item
either:

- `pass` — the named artefact has been inspected and the criterion is met.
- `fail` — the criterion is not met; a remediation action is recorded.
- `n/a` — the criterion does not apply (with a one-line justification).

`pass` requires direct inspection of the named artefact. A reviewer may not
mark an item `pass` on the basis of a verbal or summary report.

References, in order of precedence:

1. `docs/procurement/data_vendor_request.md` — vendor questions on file.
2. `docs/PROCUREMENT.md` — Day 0 outbound rules; fallback when the
   per-vendor request file is silent on a topic.
3. Appendix C (`docs/appendices/C_data_qa_partitioning.md`) — the
   pre-code sign-off this checklist supports.

---

## 1. Vendor verification

The vendor request files in `docs/procurement/data_vendor_request.md`
enumerate the questions to which the vendor must reply in writing before
the partition lock is binding. If that file is silent on a topic, the
fallback is the Day 0 rule in `docs/PROCUREMENT.md` (primary + secondary
required, secondary independent of primary's upstream where possible, no
backtest pass/fail on placeholder data).

1. [ ] Primary vendor reply is on file under `docs/vendor-replies/` (or a
       gitignored NDA-restricted file with a metadata stub committed),
       answering all eleven items in §"Request body — Primary" of
       `docs/procurement/data_vendor_request.md`. Items left unanswered are
       enumerated in this checklist row.
2. [ ] Secondary vendor reply is on file with the same coverage, and item
       1 of the secondary request (independence of upstream feed) is
       answered with a description of the upstream source. If the
       secondary shares an upstream with the primary, that is disqualifying
       and triggers a re-source action; this row is `fail` until a
       compliant secondary reply is on file.
3. [ ] Earliest available MES tick date from each vendor is recorded and
       both cover the candidate training start (`2019-05-06`) without a
       leading gap. A vendor whose history begins after `2019-05-06` is
       acceptable only if the partition draft is revised (or the ES-proxy
       rule §5 of `docs/data/partition_plan.md` is invoked), and the
       revision is recorded.
4. [ ] Earliest available MES BBO date from each vendor is recorded and
       coverage matches or exceeds the tick coverage for the same
       partition span. BBO-shorter-than-tick is flagged in this row.
5. [ ] Tick precision per vendor is recorded (expected: `0.25` for MES
       outright). Any sub-tick fields are enumerated.
6. [ ] Revisions / corrections policy per vendor is recorded with a clear
       answer to: are historical files revised after publication, and can
       we pin to an immutable as-of snapshot? "Files may be revised
       silently" is `fail` for this row.
7. [ ] Pricing tier and redistribution constraints are recorded for both
       vendors. A redistribution constraint that prevents committing
       sample data to the repo (even gitignored) is flagged so that
       Appendix C reviewer is aware.
8. [ ] Vendor SLA for outages is recorded for each vendor and is at least
       reviewed against the program's own latency / availability targets
       in §H.

## 2. Cross-vendor parity

Cross-vendor reconciliation is the principal defence against silent
single-vendor errors. Appendix C §5.5 requires a sample window, a
per-field tolerance, and a decision rule with a single named owner.

1. [ ] **Sample window** is specified: a contiguous trading session in the
       middle of the candidate training partition, e.g., one full RTH +
       overnight session of MES from a week with no scheduled half-day
       and no top-tier macro release. Window size: not less than one full
       session; not more than five sessions for the initial parity
       check.
2. [ ] **Tolerance for tick disagreement** is specified per field:
       - Price: zero tolerance after rounding to 0.25; any disagreement
         is recorded.
       - Trade size: zero tolerance.
       - Trade timestamp: per-tick disagreement up to one exchange-feed
         clock tick (vendor-stated precision; typically microsecond) is
         tolerated; larger disagreements are recorded.
       - BBO best bid / best offer price: zero tolerance after rounding;
         any disagreement is recorded.
       - BBO size: tolerance specified explicitly (e.g., zero, or a
         vendor-stated rounding rule). The chosen tolerance and its
         justification are recorded.
3. [ ] **Decision rule on mismatch** is specified and names a single
       owner. The default rule template is: "If tick-level disagreements
       on price or trade size exceed N rows or P percent of the sample,
       primary is provisionally rejected pending re-pull; the named
       owner (Risk Reviewer) decides whether to escalate, re-source, or
       accept with a documented carve-out." The actual N and P are set
       at this checklist's review.
4. [ ] **Reconciliation artefact** is committed: a CSV / parquet of the
       diff rows from the sample window, with the sample window itself
       reproducible (vendor file paths, file hashes, as-of dates).
5. [ ] **Logging**: the cross-vendor reconciliation pass is recorded as
       a `data_qa_check` row in
       `docs/research_contamination_log/research_contamination_log.csv`
       with `dataset_used = none` (the reconciliation is on raw data, not
       on a partition) and a description that names both vendor files and
       the diff artefact.

## 3. Gap policy and treatment

Gaps in tick / BBO data are unavoidable; the question is whether they are
detected, disclosed, and treated consistently.

1. [ ] **Detection rule** is specified per data class:
       - Tick: an inter-trade interval longer than M seconds during RTH, or
         longer than M' seconds during overnight, is flagged. M and M' are
         set per the vendor's published gap policy and the session
         schedule in `configs/sessions/mes.yml`.
       - BBO: an inter-quote interval longer than Q seconds, or a missing
         BBO row at a session boundary, is flagged.
       - Bar: a missing 5m or 60m bar (per §B.5) is flagged regardless of
         whether the underlying tick gap is below threshold, because bar
         construction is intolerant to gaps.
2. [ ] **Recording location** is specified: each detected gap is written
       to a structured gap-log file alongside the dataset (filename
       convention: `gaps_<symbol>_<date>.csv` next to the source file) and
       summarised in the ingestion manifest.
3. [ ] **Downstream effect** is specified per gap class. Allowed actions:
       `drop` (the bar / row is excluded), `flag` (kept, marked, used only
       in non-statistical contexts), `re_pull` (an automatic or manual
       re-pull of the source window). No gap class is unmapped. This
       mapping mirrors Appendix C §5.6.
4. [ ] **Re-pull threshold** is specified: above what cumulative gap
       fraction (e.g., 1 percent of an RTH session) does the affected
       trading day get marked `re_pull` rather than `flag`?
5. [ ] **Escalation**: any gap that survives a re-pull is escalated to
       the Risk Reviewer, who decides whether the affected calendar date
       is excluded from the relevant partition. The exclusion is logged
       and disclosed in any research report that uses the partition.

## 4. Corporate actions

MES is a futures contract; corporate actions in the equity sense (splits,
dividends, mergers) do not apply to the front-month future. Roll handling,
however, is the futures equivalent of a corporate action and must be
treated with the same rigour. This section explicitly calls out roll
handling and confirms the no-corporate-action assumption is correct.

1. [ ] Vendor confirms in writing that no corporate-action adjustments
       apply to MES (response to question 5 of the primary request and
       question 6 of the secondary). A "we adjust for X" answer is
       investigated and the adjustment is either documented and
       accepted, or the vendor is rejected.
2. [ ] Quarterly contract expiry dates for MES (March, June, September,
       December — H, M, U, Z cycle) are listed for the candidate
       training, validation, and final-holdback windows.
3. [ ] Symbol-change events (e.g., front-month rolling from MESM5 to
       MESU5) are enumerated with the convention used by each vendor for
       their symbol naming. Disagreement on naming convention is flagged
       to the parser implementer; it does not by itself reject a vendor.
4. [ ] Roll handling itself is covered in §5; this row is `pass` only if
       §5 is also `pass`.

## 5. Roll handling

The continuous-contract construction is the highest-impact data choice in
this program. A wrong choice silently distorts every backtest result.

1. [ ] **Roll method** is specified: calendar-based roll (e.g., five
       sessions before expiry) versus volume-based roll (roll on the
       first session that next-month volume exceeds front-month volume).
       The choice is recorded with a one-paragraph rationale that names
       the alternative and explains why it was rejected.
2. [ ] **Stitching convention** is specified: back-adjusted versus
       ratio-adjusted versus unadjusted (panel of contracts, no
       continuous series). The choice is recorded with a rationale. If
       back-adjusted, the back-adjustment is applied at the price level
       (not the bar level) and historic prices below zero are explicitly
       allowed or rejected as a policy. If ratio-adjusted, the ratio
       reference contract is named.
3. [ ] **Choice rationale** addresses the trade-off: back-adjusted
       preserves price level relationships within a contract but distorts
       absolute levels across rolls; ratio-adjusted preserves percentage
       returns at the cost of distorting price levels. The rationale must
       state which property the v0.2 strategy spec depends on, and pick
       accordingly. If the strategy spec is silent, the conservative
       default is **back-adjusted with explicit roll markers** so that
       any roll-touching feature can be detected and excluded from a
       statistic.
4. [ ] **Roll markers** are present in the produced continuous file: a
       boolean / categorical column flags every bar that is the first or
       last bar of a contract within the continuous series, and the
       contract identifier is preserved per row.
5. [ ] **Reconciliation across vendors**: roll dates from primary and
       secondary are compared. A roll-date disagreement of more than one
       session is `fail` for this row and triggers escalation to the
       Risk Reviewer.
6. [ ] **Documentation**: the roll method, stitching convention, and the
       calendar of applied rolls are documented under `docs/data/`
       (filename TBD; this checklist row references that document by
       path once it exists).

## 6. Timestamp source verification

The contamination guard, the fill model, and the bar builder all assume
exchange-sourced timestamps. Vendor-restamped timestamps invalidate
intra-bar fill assumptions and any latency-bounded statistic.

1. [ ] Vendor reply to question 7 (primary) and question 8 (secondary)
       of the data vendor request is on file and states whether
       timestamps are taken directly from the CME exchange feed or
       re-stamped at the vendor gateway. Required answer: **exchange**.
       A "re-stamped at vendor gateway" answer is `fail` for that
       vendor unless an exchange-source field is also provided alongside
       and the vendor's re-stamp is purely informational.
2. [ ] Timestamp precision is recorded per vendor (microsecond,
       nanosecond, etc.) and is at least at the precision required by
       the fill model in Appendix D.
3. [ ] Clock-sync mechanism is recorded per vendor (e.g., PTP from CME,
       GPS-disciplined, NTP).
4. [ ] A vendor that cannot certify exchange-source timestamps is
       rejected for the primary role and may serve only in the secondary
       role with the limitation disclosed in the cross-vendor parity
       artefact.
5. [ ] Cross-vendor timestamp drift on the parity sample (§2) is within
       the tolerance specified in §2.2; otherwise the offending vendor
       is investigated.

## 7. Acceptance / decline conditions

These are the binary outcomes the reviewer signs into.

**Acceptance** of a vendor and partition draft requires all of:

1. [ ] Both vendors have a reply on file (§1.1, §1.2).
2. [ ] Independence of secondary upstream is established (§1.2).
3. [ ] Cross-vendor parity check is committed and within tolerance
       (§2.4, §2.5).
4. [ ] Gap policy has no unmapped class (§3.3).
5. [ ] Corporate-action handling is confirmed not-applicable, and roll
       handling is documented and reconciled across vendors (§4, §5).
6. [ ] Both vendors certify exchange-source timestamps (§6.1) at the
       precision required by Appendix D (§6.2).
7. [ ] The partition draft `configs/data_partitions.draft.yml` has
       `no_overlap_verified: true` (set by the reviewer per §6 of
       `docs/data/partition_plan.md`).
8. [ ] No item in §§1–6 above is `fail`.

**Decline** is recorded if any of:

1. A primary vendor cannot certify exchange-source timestamps and no
   alternative primary is identified.
2. The secondary vendor shares an upstream with the primary and no
   independent secondary is available; the cross-check defence is then
   absent.
3. Cross-vendor parity exceeds the §2 tolerance and a re-pull does not
   resolve the disagreement.
4. The vendor's revisions policy permits silent post-publication revision
   without an as-of pin.
5. Roll-date disagreement between vendors exceeds one session and is not
   resolved.
6. Any gap class in §3.3 is left unmapped after review.

A decline is recorded with a written remediation path (re-source, narrow
the partition, invoke ES-proxy with disclosure, etc.). A decline is not a
project-blocker; it is a trigger for the next round of procurement or for
a revision of the partition draft.

## 8. What this checklist does NOT do

- Does **not** sign Appendix C. The Risk Reviewer signs Appendix C
  separately, having used this checklist as supporting evidence.
- Does **not** sign the production lock file
  (`configs/data_partitions.yml`). The Director Sponsor signs that.
- Does **not** authorise any v0.2 backtest. That gate additionally
  requires the broker rate sheet (errata §5) and the broader procurement
  set in `docs/PROCUREMENT.md`.
- Does **not** load any market data. Sample-window inspection performed
  under §2 is permitted only on a window outside the candidate
  validation and final-holdback ranges, and is logged as a
  `data_qa_check` against `dataset_used = none` per
  `docs/research_contamination_log/README.md`.
