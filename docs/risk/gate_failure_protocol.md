# Gate failure protocol

**Owner:** Risk Reviewer (independent — see `docs/OWNERS.md`)
**Scope:** What happens when a gate from `docs/GATES.md` fails. One
section per gate. Each section names the decision-maker, the evidence
required, who must be informed, and where the decision is recorded.
**Status of file:** Authoritative. No gate failure may be recovered
from informally — every failure is recorded as a contamination-log row
and (where applicable) a `configs/signoff_matrix.yml` row update with
`signed: false` and a `notes:` pointer to the failure record.

This protocol is read alongside:

- `docs/GATES.md` — the gate state machine.
- `docs/risk/contamination_review_checklist.md` — concurrent review.
- `docs/risk/validation_freeze_checklist.md` — pre-OOS gate.
- `docs/research_contamination_log/README.md` — log schema, "Append-only
  rule" (lines 20-30), rejection language (lines 9-12, 56-60).
- `docs/v1.4r1_errata_and_kickoff.md` — gate clarifications.

---

## 1. Pre-code sign-off failure (Appendices B, C, D, E, H)

Failure means: any of rows `B`, `C`, `D`, `E`, `H` in
`configs/signoff_matrix.yml` cannot be signed because review uncovered
an unresolved issue in the corresponding appendix.

- **Decision-maker:** the appendix owner per `docs/OWNERS.md`
  (Director Sponsor for B, Risk Reviewer for C, Engineering for D and
  H, Quant for E).
- **Evidence required:** written objection naming the appendix section,
  the gap, and the proposed remedy. Filed as a Change Request per
  `docs/v1.4r1_errata_and_kickoff.md:88-90`.
- **Re-review:** the failed appendix is reopened. Other pre-code
  appendices may continue review in parallel, but no v0.2 strategy
  code may land until all five rows are signed (`docs/GATES.md:6`).
- **Re-signers:** the original signer per `docs/OWNERS.md`. A backup
  may sign only if the primary is unavailable and the backup is not
  the same individual as the Risk Reviewer.
- **Who is informed:** Director Sponsor and Risk Reviewer always;
  other workstream owners as relevant.
- **Recorded at:** `configs/signoff_matrix.yml` `notes` field (with
  the CR id) and a contamination-log row (`action_type=other`,
  `decision=escalated`).

## 2. Approved-backtest failure

Failure means: a v0.2 backtest variant on training (post broker-rate-
sheet substitution) did not meet §E pre-OOS criteria, or surfaced a
spec violation.

- **Decision-maker:** Quant owner.
- **Evidence required:** backtest report (no `D2_PLACEHOLDER` per
  `docs/GATES.md:33-35`), registry `entry_id`, and contamination-log
  rows for parameter / rule changes that produced the variant.
- **Outcome:** a contamination-log row is appended with
  `decision=logged_for_next_version`; the description names the
  failing §E criterion and the observed metric.
- **Disposition:** the variant is not carried forward to validation. A
  new variant requires a new registry entry (and a new
  `strategy_version` if rules change, per §B.13). The validation
  partition remains untouched for any subsequent variant whose
  registration precedes the OOS query.
- **Who is informed:** Risk Reviewer and Director Sponsor.
- **Recorded at:** contamination log; registry
  (`src/algotrading/registry/registry.py:111`).

## 3. OOS pass / fail (validation partition)

Failure means: the one-shot OOS query for a `strategy_version` did
not meet §E.2 / §E.3 OOS criteria.

- **Decision-maker:** Quant owner calls pass/fail against written §E
  criteria; Risk Reviewer audits the contamination log to confirm the
  freeze row preceded the query and that no second query was issued.
- **Evidence required:** OOS report, the `validation_freeze` row (per
  `docs/risk/validation_freeze_checklist.md`), the
  `dataset_used=validation` row recording the query, and a registry
  entry whose `registered_at` precedes the query timestamp.
- **Outcome on fail:** the strategy version is rejected. A
  `decision=logged_for_next_version` row records the failure metric
  and missed §E criterion. **The validation partition is burned for
  this `strategy_version`** — any successor must be a new
  `strategy_version` with a new registry entry (§B.13, errata §6).
- **Outcome on pass:** the family proceeds to final-holdback only if
  the trade-count threshold is met (`docs/GATES.md:9`).
- **Who is informed:** Risk Reviewer, Director Sponsor, Engineering.
- **Recorded at:** contamination log; `configs/signoff_matrix.yml`
  `validation_freeze` `notes` annotated (the row itself remains
  signed — the freeze succeeded; only OOS evaluation failed).

## 4. Final-holdback pass / fail (binding, family-level)

Failure means: the family-level final-holdback evaluation did not meet
the §E binding criteria. Per errata §6
(`docs/v1.4r1_errata_and_kickoff.md:51`), the holdback partition is
binding family-level regardless of v0.2 / v0.3 inheritance.

- **Decision-maker:** Director Sponsor, on the joint recommendation of
  Quant and Risk Reviewer.
- **Evidence required:** holdback report, OOS pass record for every
  variant in the family, family-level registry summary, and a
  contamination audit confirming no holdback queries preceded the
  formal evaluation.
- **Outcome on fail:** the **entire family** is rejected. A new family
  requires a new top-level family identifier; no carry-over of
  holdback data is permitted (`docs/GATES.md:9`).
- **Outcome on pass:** the family proceeds to the paper gate, subject
  to Appendix F finalization for the chosen broker. Appendix I is a
  scope-control note for internal-only scope (see
  `docs/appendices/I_legal_scope_note.md`); it does not gate paper or
  internal live trading. Counsel review is required only on a
  scope-expansion trigger.
- **Who is informed:** all workstream owners.
- **Recorded at:** contamination log (`action_type=other`,
  `decision=escalated` on fail); family-level verdict recorded in the
  registry as a new entry whose `note` field carries the result.

## 5. Paper-gate failure

Failure means: paper-trading metrics under §E.3 do not meet criteria,
or operational issues (broker, OCO, fills) diverged materially from
the simulator.

- **Decision-maker:** Director Sponsor, on the joint recommendation of
  Ops, Quant, and Risk Reviewer.
- **Pre-conditions** (`docs/GATES.md`): row `F` signed. Appendix I is a
  scope-control note for internal-only scope and is not a paper-gate
  pre-condition; counsel review is required only on a scope-expansion
  trigger.
- **Evidence required:** paper session reports, divergence analysis vs
  simulator (fill model, slippage, latency per
  `src/algotrading/monitoring/`), contamination-log rows for every
  paper session (`dataset_used=paper`), and Ops sign-off on broker-
  side facts.
- **Outcome on fail:** strategy returns to backtest-only status. Row
  `paper` reverts to `signed: false` with a `notes` pointer to the
  failure record. A new paper attempt requires either (a) a fix that
  does not change strategy rules — fully logged Ops/Engineering
  remediation — or (b) a new `strategy_version`.
- **Who is informed:** all workstream owners.
- **Recorded at:** contamination log (`action_type=other`,
  `decision=escalated`); `configs/signoff_matrix.yml` row `paper`.

## 6. Small-size live failure

Failure means: real-capital execution at minimum size breached a
§E.3-defined live tripwire (drawdown, losing streak, daily loss,
operational incident).

- **Decision-maker:** Director Sponsor; Risk Reviewer holds an
  independent veto if the failure indicates a contamination issue
  (e.g., undisclosed parameter edits during paper).
- **Pre-conditions** (`docs/GATES.md:11`): the paper gate was signed.
- **Evidence required:** trade-by-trade reconciliation vs broker
  statements, the §E.3 tripwire that fired, `dataset_used=live` rows
  in the contamination log, and the bound values from
  `configs/risk_limits.yml`.
- **Outcome on fail:** trading is halted; capital returned to flat per
  §H. Row `small_size_live` reverts to `signed: false`. Re-entry
  requires a paper-gate re-pass (if execution-side) or a new
  `strategy_version` (if rules changed).
- **Who is informed:** all workstream owners; counsel if any external
  party is affected.
- **Recorded at:** contamination log; `configs/signoff_matrix.yml`
  row `small_size_live`; daily log under `configs/sessions/`.

## 7. Scale-up failure

Failure means: post-scale-up performance (size > 1 MES) materially
diverged from small-size live, or any §G criterion was breached.

- **Decision-maker:** Director Sponsor.
- **Pre-conditions** for scale-up at all (`docs/GATES.md:12`): row `G`
  (Appendix G) signed in `configs/signoff_matrix.yml`.
- **Evidence required:** rolling performance comparison vs small-size
  live, the §G criteria report, and Risk Reviewer audit of the
  contamination log for the post-paper period.
- **Outcome on fail:** size returns to small-size live (or flat if
  warranted). Row `G` reverts to `signed: false` with `notes` pointing
  at the failure record. A new scale-up attempt requires a fresh
  Appendix G review.
- **Who is informed:** all workstream owners.
- **Recorded at:** contamination log (`action_type=other`,
  `decision=escalated`); `configs/signoff_matrix.yml` row `G`.

---

## Strategy rejection

The following findings are **automatic rejection** without further
review — independent of which gate is in flight. The Risk Reviewer
records the rejection and refuses the gate signature; no downstream
decision-maker may override.

1. **Contamination findings.** Any condition in
   `docs/risk/contamination_review_checklist.md` "Decline conditions"
   (validation peek, premature paper / live, in-place edit, schema
   corruption, forbidden Sprint 1 code, image artefacts, registry /
   log mismatch, independence breach).
2. **Undisclosed exploration.** Any variant in the registry, source,
   or research artefacts with no contamination-log row at or before
   its `registered_at`. Per
   `docs/research_contamination_log/README.md:9-12`: "Strategies
   whose contamination logs reveal undisclosed exploration are
   rejected without further review."
3. **Append-only breach.** Any historical row of
   `research_contamination_log.csv` modified or removed in `git`
   history (per `docs/research_contamination_log/README.md:20-30`).
4. **Independence breach.** Any signer overlap between the Risk
   Reviewer and Engineering / Quant / Director Sponsor on the same
   family (`docs/OWNERS.md:18-23`).

A rejected strategy does not return to the gate it was attempting; it
exits the pipeline. Re-entry is governed by the next section.

## Re-entry

A rejected strategy may re-enter only as a **new `strategy_version`
with a new registry entry**, per §B.13 (errata §6,
`docs/v1.4r1_errata_and_kickoff.md:47-54`).

- A new `strategy_version` identifier is allocated; the prior is
  retired and may not be reused. A new entry is appended via
  `StrategyRegistry.append(...)`
  (`src/algotrading/registry/registry.py:111`) with the new rules and
  a fresh `rules_hash`; if the new rules build on the prior rules,
  `supersedes` is set to the prior `entry_id`.
- A contamination-log row is appended marking inception
  (`action_type=other`, description naming the prior rejection date,
  prior `entry_id`, and the rationale).
- OOS reuse: the prior OOS partition is clean for the new version
  **only if** the new entry's `registered_at` precedes the prior OOS
  query timestamp in the log. Otherwise it is contaminated and serves
  as diagnostic comparison only — never as pass/fail. This is errata
  §6 in full force.
- The final-holdback partition remains binding family-level: a
  family-level rejection (§4) blocks the entire family — re-entry
  requires a new family identifier.
- All version-specific sign-offs (`validation_freeze`, `paper`,
  `small_size_live`, `G`) revert to `signed: false`.

No re-entry is permitted for an independence-breach rejection until
`docs/OWNERS.md` is updated via the `owners-change` PR process
(`docs/OWNERS.md:26-33`) and the new owner set has been ack'd by the
Risk Reviewer and Director Sponsor.
