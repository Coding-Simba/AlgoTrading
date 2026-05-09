# Director-set values — fillable template, v1.4-r1

**Status:** Draft worksheet for the Director Sponsor.
**Issued:** 2026-05-09
**Owner:** Director Sponsor
**Target config:** `configs/risk_limits.yml` (values are copied here once
this template is filled, reviewed, and counter-signed).
**Independence rule:** the Risk Reviewer who counter-signs this template
**must not** also be the Engineering, Quant, or Director Sponsor on this
family (`docs/OWNERS.md`).

This template records the six binding risk values before they land in
`configs/risk_limits.yml`. Values are blank by default; the Director
Sponsor fills them, captures rationale, and submits the worksheet on the
same PR that flips `locked: true` in the config file.

Cross-reference summary (informational; full checks live in
`docs/signoff/pre_code_checklist.md` §6):

- `allocated_capital_usd` is the denominator for the ROR threshold and
  for the percent-based drawdown ceilings.
- `daily_loss_limit_usd` is **subordinate** to
  `aggregate_program_drawdown_limit_pct` — a single session must not be
  able to saturate the program-level limit.
- `max_acceptable_losing_streak` interacts with the position-sizing rule:
  the worst-case loss path of length N under the chosen sizing rule must
  not breach the aggregate drawdown ceiling before N is reached.

---

## 1. allocated_capital_usd

| Field            | Value |
| ---------------- | ----- |
| Name             | allocated_capital_usd |
| Units            | USD   |
| Type             | number (> 0) |
| Valid range      | (0, +inf) |
| Dependency notes | Denominator for ROR threshold; basis for percent-based drawdown ceilings; appears in `configs/risk_limits.yml`. |
| Value            |       |
| Rationale (1 line) |     |

## 2. max_oos_drawdown_pct

| Field            | Value |
| ---------------- | ----- |
| Name             | max_oos_drawdown_pct |
| Units            | percent of `allocated_capital_usd` |
| Type             | number (percent) |
| Valid range      | (0, 100); typically `<= aggregate_program_drawdown_limit_pct` |
| Dependency notes | OOS-gate ceiling per Appendix E; cannot be looser than the program-level aggregate drawdown limit. |
| Value            |       |
| Rationale (1 line) |     |

## 3. max_acceptable_losing_streak

| Field            | Value |
| ---------------- | ----- |
| Name             | max_acceptable_losing_streak |
| Units            | consecutive losing trades (count) |
| Type             | int (>= 1) |
| Valid range      | [1, +inf) |
| Dependency notes | Interacts with position sizing: under the chosen sizing rule, the worst-case loss path of this length must not breach `aggregate_program_drawdown_limit_pct`. Used as kill-switch input by Appendix H operational controls. |
| Value            |       |
| Rationale (1 line) |     |

## 4. daily_loss_limit_usd

| Field            | Value |
| ---------------- | ----- |
| Name             | daily_loss_limit_usd |
| Units            | USD per session |
| Type             | number (> 0) |
| Valid range      | (0, `aggregate_program_drawdown_limit_pct * allocated_capital_usd / 100`) — strictly less than the program ceiling. |
| Dependency notes | Subordinate to `aggregate_program_drawdown_limit_pct`. A single-session loss must not saturate the program-level drawdown ceiling. Drives the per-session kill switch. |
| Value            |       |
| Rationale (1 line) |     |

## 5. aggregate_program_drawdown_limit_pct

| Field            | Value |
| ---------------- | ----- |
| Name             | aggregate_program_drawdown_limit_pct |
| Units            | percent of `allocated_capital_usd` |
| Type             | number (percent) |
| Valid range      | (0, 100); >= `max_oos_drawdown_pct`. |
| Dependency notes | Program-level ceiling. Anchors the ROR threshold and the daily loss-limit ratio. Triggers shutdown of the program if breached. |
| Value            |       |
| Rationale (1 line) |     |

## 6. risk_of_ruin_threshold_pct

| Field            | Value |
| ---------------- | ----- |
| Name             | risk_of_ruin_threshold_pct |
| Units            | percent (probability ceiling) |
| Type             | number (percent) |
| Valid range      | (0, 100), but realistically small (e.g., low single digits). |
| Dependency notes | Must be consistent with `allocated_capital_usd`, `aggregate_program_drawdown_limit_pct`, and the planned losing-streak length: the analytical ROR computed under the proposed sizing rule must lie below this threshold. |
| Value            |       |
| Rationale (1 line) |     |

---

## 7. External / client capital scope (errata §4)

If external or client capital is in scope at any point **before** v0.2
strategy code begins, Appendix I sign-off becomes a coding prerequisite
(errata §4) and must be signed by Legal before code lands. Internal
proprietary capital alone does not invoke this prerequisite for the
pre-code gate.

| Field                                                   | Value |
| ------------------------------------------------------- | ----- |
| External / client capital in scope before strategy code? (yes / no) |       |
| If yes — Appendix I PR / sign-off date                  |       |
| If yes — Legal signer name                              |       |
| Notes                                                   |       |

If "yes" is recorded above, the gate state remains "Now" until Appendix I
is signed off by Legal regardless of the other rows in this template.

## 8. Sign-off

The Director Sponsor signs this worksheet, then a Risk Reviewer (distinct
individual per `docs/OWNERS.md`) counter-signs to certify independence and
that the sanity checks in `docs/signoff/pre_code_checklist.md` §6 have
been performed.

### 8.1 Director Sponsor

| Field           | Value |
| --------------- | ----- |
| Signer name     |       |
| Role            | Director Sponsor |
| Date (ISO-8601) |       |
| Notes           |       |

### 8.2 Risk Reviewer counter-sign

| Field                                                       | Value |
| ----------------------------------------------------------- | ----- |
| Signer name                                                 |       |
| Role                                                        | Risk Reviewer |
| Date (ISO-8601)                                             |       |
| Independence ack (not Engineering / Quant / Director Sponsor) |     |
| Sanity checks performed (cite checklist §6 items 2–5)       |       |
| Notes                                                       |       |

Once both signatures are present, the values may be copied into
`configs/risk_limits.yml` and `locked: true` set on the same PR.

*End of Director-set values template.*
