# Appendix B — Strategy Spec v0.3

**Status:** Pre-code sign-off candidate (registered via CR-001 §B.13)  
**Scope:** v0.3 raw signal test only  
**Strategy family:** Intraday-Mean-Reversion-to-VWAP (in MES_intraday family)  
**Instrument:** MES  
**Session:** CME RTH only  
**No regime filter in v0.3.** v0.4 supplies the switch externally.  
**No optimization. No chart inspection. No backtest before broker costs are inserted. No OOS before validation freeze.**

---

## B_v0.3.1 Purpose

Canonical pre-code spec for v0.3 — intraday mean-reversion to session
VWAP. Implements the anti-correlated edge to v0.2: trades reversion in
non-aligned regimes where v0.2's continuation logic is most adverse.

## B_v0.3.2 Instrument and session

Identical to v0.2 §B.2:

- MES front-month, rolled per Appendix C
- US RTH only, America/New_York
- Earliest signal-bar close: 10:35:00 ET
- Latest signal-bar close: 15:30:00 ET
- Forced flat: 15:58:00 ET
- Half-days: no trading
- **Max trades per RTH session: 3** (combined across v0.2 and v0.3 — see B_v0.3.10)
- **One open position maximum** (combined across v0.2 and v0.3)

## B_v0.3.3 Bar timing

Identical to v0.2 §B.3.

## B_v0.3.4 60-minute RTH bars

Identical to v0.2 §B.4. Used only for the trend-alignment exclusion in
B_v0.3.6.

## B_v0.3.5 Indicators

Identical to v0.2 §B.5. v0.3 uses only:

- 5m ATR(14)
- Session VWAP from raw tick prints
- 60m EMA50, 60m EMA200 (for trend-alignment exclusion in B_v0.3.6)

## B_v0.3.6 Long entry rules

Evaluate at `T_close`.

A long signal is valid only if all conditions are true:

1. `10:35:00 ET <= T_close <= 15:30:00 ET`
2. Most recently closed 60m RTH bar exists and is from the current session.
3. **Trend-alignment exclusion**: it is NOT the case that on the most
   recently closed 60m RTH bar `EMA50 < EMA200` AND `60m close < EMA200`.
   (We do not fade strong downtrends.)
4. **Extension condition**: `5m close <= session_VWAP - 1.5 * ATR(14)` on
   the signal bar. ATR(14) is the 5m Wilder ATR ending at the signal bar.
5. **Stalling pattern**: `signal_bar.low > prior_bar.low`. The most
   recent bar failed to make a new low after the extension.
6. **Wick rejection**: `signal_bar.close > signal_bar.low + 0.3 * (signal_bar.high - signal_bar.low)`.
7. No open position (across v0.2 and v0.3).
8. No more than 2 prior trades entered in the current RTH session.
9. No active no-trade condition (B_v0.3.8).
10. Latency gates pass.

### Long stop and target

At decision time:

```text
expected_entry   = current ask + modeled slippage
candidate_stop   = lowest low of the 3-bar window ending at the signal bar - 1 tick
candidate_R      = expected_entry - candidate_stop
candidate_target = floor( session_VWAP at signal bar ) -- nearest valid tick, DOWN
```

Skip if:

```text
candidate_R > 1.5 * ATR(14)
candidate_R < 0.5 * ATR(14)
candidate_R <= 0
candidate_target - expected_entry < 0.5 * ATR(14)   # target too close
candidate_target <= expected_entry                  # VWAP not above entry
```

On actual fill:

```text
actual_R = actual_entry_fill - stop_price
target   = floor( session_VWAP at fill time ) to nearest valid tick, DOWN
```

If `actual_R <= 0` or `target <= actual_entry_fill`, transition to `ERROR_HALTED`.

## B_v0.3.7 Short entry rules

Exact mirror of long.

A short signal is valid only if all conditions are true:

1. `10:35:00 ET <= T_close <= 15:30:00 ET`
2. Most recently closed 60m RTH bar exists and is from the current session.
3. **Trend-alignment exclusion**: it is NOT the case that on the most
   recently closed 60m RTH bar `EMA50 > EMA200` AND `60m close > EMA200`.
4. **Extension condition**: `5m close >= session_VWAP + 1.5 * ATR(14)`.
5. **Stalling pattern**: `signal_bar.high < prior_bar.high`.
6. **Wick rejection**: `signal_bar.close < signal_bar.high - 0.3 * (signal_bar.high - signal_bar.low)`.
7. No open position.
8. No more than 2 prior trades entered in the current RTH session.
9. No active no-trade condition.
10. Latency gates pass.

### Short stop and target

```text
expected_entry   = current bid - modeled slippage
candidate_stop   = highest high of the 3-bar window ending at the signal bar + 1 tick
candidate_R      = candidate_stop - expected_entry
candidate_target = ceil( session_VWAP at signal bar ) -- nearest valid tick, UP
```

Skip if:

```text
candidate_R > 1.5 * ATR(14)
candidate_R < 0.5 * ATR(14)
candidate_R <= 0
expected_entry - candidate_target < 0.5 * ATR(14)
candidate_target >= expected_entry
```

On actual fill:

```text
actual_R = stop_price - actual_entry_fill
target   = ceil( session_VWAP at fill time ) to nearest valid tick, UP
```

If `actual_R <= 0` or `target >= actual_entry_fill`, transition to `ERROR_HALTED`.

## B_v0.3.8 No-trade conditions

Identical to v0.2 §B.8. v0.3 reuses the v0.2 `NoTradeContext` /
`blocking_reasons` surface unchanged.

## B_v0.3.9 News flatten

Identical to v0.2 §B.9.

## B_v0.3.10 Forced session-end flatten and cross-strategy session counters

Identical to v0.2 §B.10. Session counters are *combined* across v0.2 and
v0.3: total entries by either strategy in the same RTH session must not
exceed 3, and only one open position may exist at a time across both
strategies. The v0.4 switch policy enforces this externally by selecting
at most one of {v0.2, v0.3} as the active strategy per regime label.

## B_v0.3.11 v0.4 family rule (forward reference)

v0.4 is a regime classifier and switch policy, not a trade-generating
strategy version. It does not consume validation partitions. Its
correctness is verified by unit tests over synthetic regime inputs and
by audit of switching transitions over OOS data after v0.2 and v0.3 have
each independently passed §E gates.

## B_v0.3.12 Sign-off

| Field                | Value |
| -------------------- | ----- |
| Signed               | false |
| Director Sponsor     | DIR-01 |
| Risk Reviewer        | RISK-01 |
| Signed at ISO        | null |
| Commit hash          | null |
