# Appendix B — Strategy Spec v0.2 (sign-off template)

**Status:** Pre-code sign-off. Empty until signed; signed copies are committed
via PR.
**Frozen by:** errata §3 (pre-code sign-off rows are FROZEN).
**Canonical rule reference:** §B.13 — registry-first registration is the
controlling rule for any future v0.3 OOS / holdback claim. See errata §6.

---

## 1. Scope of this sign-off

This appendix locks the **v0.2 strategy specification** at the rule level.
Once signed, the following are binding inputs to v0.2 strategy code and may
not be edited without a Change Request:

- The B.7 / B.8 entry rules (definition, not implementation).
- Indicator definitions used by v0.2: EMA, VWAP, ATR — windows, anchoring,
  reset semantics, and tick / bar input source.
- Intended timeframes (5m primary, 60m context per §B.5).
- Session windows used for entry / exit / forced-flatten decisions.
- No-trade rules (event blackouts, half-day handling, illiquid windows).
- The registry-first rule of §B.13 as canonical.

Indicators and entry rules are **spec items**: they are signed off here even
though no v0.2 code yet implements them (Sprint 1 freeze, errata §3, §9).

## 2. What this sign-off unblocks

Per `docs/GATES.md`:

- The `v0.2 strategy code` gate. Together with C, D, E, H, signing this row
  permits implementation of B.7 / B.8 in `src/algotrading/strategies/` (not
  yet created).

This sign-off does **not** unblock approved v0.2 backtests. That gate
additionally requires the broker rate sheet to replace `D2_PLACEHOLDER`
costs (errata §5).

## 3. Dependencies on other appendices

- **Appendix C** (data + partitions): the v0.2 spec is meaningless without a
  locked partition file. Reviewer must confirm `configs/data_partitions.yml`
  is on track to be locked before any v0.2 query runs.
- **Appendix D** (fill model): execution semantics in B.7 / B.8 (stop
  triggers, bracket behaviour) must be consistent with the print-through and
  intrabar collision rules in D.
- **Appendix H** (ops): forced-flatten rules in this appendix must be
  expressible by the order state machine in `src/algotrading/orders/`.

## 4. Source modules and tests referenced

- `src/algotrading/registry/registry.py` — `StrategyRegistry`, append-only,
  hash-addressed entries. §B.13 enforcement point.
- `src/algotrading/calendar/calendar.py` — session windows used by no-trade
  and forced-flatten rules.
- `src/algotrading/bars/bars.py` — 5m / 60m bar boundaries (§B.5).
- `configs/sessions/mes.yml` — placeholder calendar; real calendar lands
  with the procurement reply (`docs/PROCUREMENT.md`).
- `tests/test_registry.py`, `tests/test_calendar.py`, `tests/test_bars.py`.

## 5. Review checklist

The signer must verify each item below by direct inspection (not by
asking the author). Initial each box. Unchecked items block the signature.

1. [ ] B.7 entry rule is fully specified: trigger condition, side
       determination, order type, price reference, time-in-force, and the
       set of input bars (5m primary vs 60m context per §B.5) are each
       written down with no "TBD" tokens.
2. [ ] B.8 entry rule is fully specified to the same bar above. If B.8 is a
       variant of B.7, the diff is stated explicitly (which fields differ
       and which are inherited).
3. [ ] EMA definition: window length, price input (close vs typical),
       seeding rule for the first N bars, and behaviour across session
       boundaries (carry vs reset) are written down.
4. [ ] VWAP definition: anchoring point (session open vs rolling), reset
       rule on session close, and tick-vs-bar input source are written
       down.
5. [ ] ATR definition: period, true-range formula, and behaviour at the
       first bar of a session (with no prior close) are written down.
6. [ ] Session windows for entry, exit, and forced-flatten are specified by
       reference to `configs/sessions/mes.yml` schema (regular, half_day,
       holiday, overnight). Half-day and holiday handling is explicit, not
       implied.
7. [ ] No-trade rules enumerate: scheduled economic releases (with lead /
       lag minutes), open / close avoidance windows, and any liquidity
       filter. Each rule names the data source it depends on.
8. [ ] Forced-flatten timing is specified to the second relative to the
       session close, and is consistent with
       `SessionCalendar.next_close_after`.
9. [ ] §B.13 registry-first rule is acknowledged in writing: the v0.2
       strategy version string is named, and the spec states that any v0.3
       must be appended to `StrategyRegistry` before any v0.2 OOS query is
       run if the v0.2 OOS partition is to remain clean for v0.3
       (errata §6).
10. [ ] The spec contains **no** numeric values that depend on broker costs;
        any cost-sensitive parameter (e.g., minimum-edge filter) is flagged
        for re-derivation once the broker rate sheet replaces the §D.2
        placeholder (errata §5).
11. [ ] The spec contains **no** queries against the validation or
        final-holdback partitions, even illustratively. All examples cite
        the training partition only.
12. [ ] No B.7 / B.8 logic is present anywhere under `src/algotrading/` at
        the time of signing (Sprint 1 freeze; errata §3, §9).
13. [ ] A v0.2 registry entry will be appended to
        `StrategyRegistry` (`src/algotrading/registry/registry.py`)
        immediately before the first line of v0.2 code is written, and
        that requirement is stated in this spec.
14. [ ] Capital and per-trade risk values used in any worked example are
        supplied by the Director Sponsor (per `docs/OWNERS.md`), not chosen
        by the strategy owner.

## 6. Sign-off block

Empty by default. To sign, fill the row, commit on a branch, and open a PR
labelled `signoff-appendix-b`. The Risk Reviewer must independently
acknowledge the PR (independence rule, `docs/OWNERS.md`).

| Field          | Value |
| -------------- | ----- |
| Signer name    |       |
| Role           |       |
| Date (ISO-8601)|       |
| Notes          |       |

Allowed roles for this appendix (per `docs/OWNERS.md`):

- Quant — baselines + validation harness (primary)
- Director sponsor (capital / risk values referenced in §5 item 14)
- Risk reviewer (independence ack, separate PR comment, not a co-signer)
