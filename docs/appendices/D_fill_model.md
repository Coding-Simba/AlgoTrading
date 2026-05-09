# Appendix D — Fill Model (sign-off template)

**Status:** Pre-code sign-off. Empty until signed; signed copies are committed
via PR.
**Frozen by:** errata §3 (pre-code sign-off rows are FROZEN; placeholder
costs in §D.2 are permitted for unit-test scaffolding only).
**Cost gating:** placeholder costs (`D2_PLACEHOLDER`) **never** appear in
approved backtests, research reports, or pass / fail evaluation
(errata §5).

---

## 1. Scope of this sign-off

This appendix locks the **fill-model rules** at the specification level,
together with the placeholder-cost discipline. Once signed, the following
are binding inputs to v0.2 strategy code and may not be edited without a
Change Request:

- The set of order types covered: market, limit, stop. Bracket
  (stop-loss + take-profit) resolution rules.
- Stop-trigger semantics: a stop is triggered when the **trade tape prints
  through** the stop price, not on a quote that touches without trading.
- Intrabar collision handling: when both stop-loss and take-profit are
  reached within the same bar and the underlying ticks cannot disambiguate
  ordering, the model records the **worst-case (stop-loss) outcome** and
  flags the result as ambiguous.
- Slippage and commission application points (per side, in ticks).
- The §D.2 placeholder discipline: any output produced with placeholder
  costs carries the tag `D2_PLACEHOLDER` and is rejected by CI from
  approved backtest, validation, and OOS contexts.

The fill-model implementation already exists in
`src/algotrading/fillmodel/model.py` as Sprint 1 framework scaffolding.
This appendix signs off the **rules** that implementation encodes and the
discipline around placeholder costs.

## 2. What this sign-off unblocks

Per `docs/GATES.md`:

- The `v0.2 strategy code` gate (jointly with B, C, E, H). v0.2 logic may
  be wired against the fill model once this row is signed.

This sign-off does **not** unblock approved v0.2 backtests. That gate
requires the broker rate sheet to **replace** §D.2 placeholders (errata
§5). Specifically: the `PlaceholderCosts` object must be supplanted by a
broker-derived cost object whose `tag` is **not** `D2_PLACEHOLDER`, and
`FillResult.is_placeholder()` must return `False` for every fill
emitted during an approved run.

## 3. Dependencies on other appendices

- **Appendix B**: B.7 / B.8 entry rules use stop and bracket order types.
  The execution semantics in B must be expressible by the model in this
  appendix.
- **Appendix E**: pass / fail thresholds in E (expectancy, Sharpe, max
  DD) cannot be applied to placeholder-cost output. E depends on D for
  placeholder cost guidance and the `D2_PLACEHOLDER` exclusion rule.
- **Appendix H**: the fill model emits fills; the order state machine
  consumes them. Bracket resolution that ends in a worst-case stop must
  drive an `OrderEvent.FILL` (not a `PARTIAL_FILL`) in H.
- **Procurement**: `docs/PROCUREMENT.md` row "Broker rate sheet" is the
  operational unblocker for replacing §D.2.

## 4. Source modules and tests referenced

- `src/algotrading/fillmodel/model.py` —
  - `FillModel.fill_market`, `fill_limit_on_tick`, `fill_stop_on_tick`
  - `FillModel.stop_triggered` (print-through semantics)
  - `FillModel.resolve_bracket_on_bar` (intrabar collision; worst-case
    stop fill; sets `ambiguous_collision=True`)
  - `PlaceholderCosts`, `D2_PLACEHOLDER_TAG`
  - `FillResult.is_placeholder`
- `src/algotrading/orders/state_machine.py` — consumes fills (Appendix H).
- `tests/test_fillmodel.py` — unit tests covering market slippage, limit
  trigger conditions, stop print-through, bracket collision worst-case,
  and the `D2_PLACEHOLDER` tag.
- `configs/sessions/mes.yml` — tick size context for prices used in tests.

## 5. Review checklist

The signer must verify each item below by direct inspection of the source
and tests above. Initial each box. Unchecked items block the signature.

1. [ ] The order types covered match the spec exactly: `MARKET`, `LIMIT`,
       `STOP`. No other order types are silently fillable. The reviewer
       has confirmed `OrderType` is the only `Enum` of order types in
       `fillmodel/model.py`.
2. [ ] `stop_triggered` uses the **trade tape** (`tick.price`), not a
       BBO quote. The reviewer has read the function and confirmed there
       is no quote-touch path that triggers a stop.
3. [ ] Stop trigger comparison is correct for both sides:
       BUY stop triggers when `tick.price >= intent.price`; SELL stop
       triggers when `tick.price <= intent.price`.
4. [ ] `resolve_bracket_on_bar` returns the worst-case (stop-loss) fill
       price when both target and stop are hit within the same bar, and
       sets `ambiguous_collision=True`. The reviewer has verified the
       branch in code, not just the test name.
5. [ ] When only one side of the bracket is reached, the model returns
       that side's fill price (target if only target, stop if only
       stop). When neither is reached, the result is unfilled with
       `notes=["bracket_pending"]`.
6. [ ] Slippage is applied with side-correct sign in `_slip`: BUY pays
       positive slippage, SELL receives negative. Slippage is zero when
       `costs is None`.
7. [ ] Commission is applied as `commission_per_side_ticks` in
       `_make_result` and is reported in `FillResult.cost_ticks`. No
       commission is applied silently outside this code path.
8. [ ] The constant `D2_PLACEHOLDER_TAG = "D2_PLACEHOLDER"` is the
       single source of truth for the placeholder marker. Every
       `PlaceholderCosts` instance carries this tag by default; every
       `FillResult` produced from `PlaceholderCosts` exposes it via
       `cost_tag` and `is_placeholder() == True`.
9. [ ] CI is configured to fail any approved-backtest output that
       contains the literal `D2_PLACEHOLDER` (errata §5). The reviewer
       has confirmed the CI rule exists or has filed an issue requiring
       it before the broker-rate-sheet substitution lands.
10. [ ] The unit tests in `tests/test_fillmodel.py` cover, at minimum:
        market slippage with sign, limit-fill trigger boundary, stop
        print-through (BUY and SELL), bracket worst-case collision with
        `ambiguous_collision`, and the `D2_PLACEHOLDER` tag round-trip.
11. [ ] No v0.2 strategy logic is present anywhere under
        `src/algotrading/` at the time of signing (Sprint 1 freeze;
        errata §3, §9). Fill-model unit tests do not import a v0.2
        strategy module.
12. [ ] `FillModel.__init__` permits `costs=None` (no costs applied),
        and a result produced in that mode does not carry the
        placeholder tag. This is the only sanctioned path for cost-free
        development assertions; it is **not** a path to approved
        output.
13. [ ] The reviewer has confirmed `PlaceholderCosts.commission_per_side_ticks`
        and `slippage_ticks` are both integer tick counts (not
        currency), so substitution by the broker rate sheet is a
        type-preserving change.

## 6. Sign-off block

Empty by default. To sign, fill the row, commit on a branch, and open a PR
labelled `signoff-appendix-d`. Per `configs/signoff_matrix.yml`, the
required `signer_role` is **Engineering**. The Risk Reviewer must
independently acknowledge the PR (independence rule, `docs/OWNERS.md`).

| Field           | Value |
| --------------- | ----- |
| Signer name     |       |
| Role            |       |
| Date (ISO-8601) |       |
| Notes           |       |

Allowed roles for this appendix (per `docs/OWNERS.md` and
`configs/signoff_matrix.yml`):

- Engineering — data + engine (primary).
- Ops — broker / OCO (ack on §D.2 substitution path; not a co-signer
  here, signs the broker rate sheet row separately).
- Risk reviewer (independence ack on the PR; not a co-signer).
