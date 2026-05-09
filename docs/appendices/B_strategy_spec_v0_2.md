# Appendix B — Strategy Spec v0.2

**Status:** Pre-code sign-off candidate
**Scope:** v0.2 raw signal test only
**Strategy family:** Trend-Pullback-Continuation
**Instrument:** MES
**Session:** CME RTH only
**No regime filter in v0.2.**
**No optimization.**
**No chart inspection.**
**No backtest before broker costs are inserted.**
**No OOS before validation freeze.**

---

## B.1 Purpose

This appendix is the canonical pre-code strategy specification for v0.2.
Engineering may implement only the rules stated here. If any
implementation detail is not stated here, it is not approved.

## B.2 Instrument and session

- Instrument: CME Micro E-mini S&P 500 futures, MES
- Contract: front-month, rolled per Appendix C
- Session: US Regular Trading Hours only
- Timezone: America/New_York
- Earliest signal-bar close: 10:35:00 ET
- Latest signal-bar close: 15:30:00 ET
- Forced flat time: 15:58:00 ET
- Half-days: no trading
- Max trades per RTH session: 3
- One open position maximum

## B.3 Bar timing

A bar labeled `T_close` contains ticks:

```text
T_open <= tick_timestamp < T_close
```

The tick at exactly `T_close` belongs to the next bar.

The signal bar is included in calculations at `T_close` because all its
ticks are strictly before `T_close`.

Entry is attempted immediately at `T_close`, subject to latency gates.

## B.4 60-minute RTH bars

Use these 60-minute RTH bars:

```text
[09:30, 10:30)
[10:30, 11:30)
[11:30, 12:30)
[12:30, 13:30)
[13:30, 14:30)
[14:30, 15:30)
```

Discard:

```text
[15:30, 16:00)
```

Do not carry the partial bar into the next session.

## B.5 Indicators

Use only these definitions:

- Standard EMA: `alpha = 2 / (N + 1)`, seeded with simple average of
  first N closed bars.
- Wilder ATR: `alpha = 1 / N`, period 14, on 5-minute bars.
- 60m EMA50
- 60m EMA200
- 5m EMA200
- 5m EMA20
- 5m ATR(14)
- Session VWAP from raw tick prints:
  `sum(price * volume) / sum(volume)`, reset at 09:30 ET.

VWAP approximation from 5m bars disqualifies clean approval.

## B.6 Long entry rules

Evaluate at `T_close`.

A long signal is valid only if all conditions are true:

1. `10:35:00 ET <= T_close <= 15:30:00 ET`
2. Most recently closed 60m RTH bar exists and is from the current
   session.
3. On that 60m bar:
   - `EMA50 > EMA200`
   - `60m close > EMA200`
4. On the 5m signal bar:
   - `5m close > 5m EMA200`
5. Pullback occurred within the last 3 closed 5m bars, including the
   signal bar:
   - at least one bar low touched or crossed below 5m EMA20 OR session
     VWAP.
6. Continuation trigger:
   - signal-bar close is strictly greater than the high of the
     immediately preceding 5m bar.
7. No open position.
8. No more than 2 prior trades entered in the current RTH session.
9. No active no-trade condition.
10. Latency gates pass.

### Long stop and target

At decision time:

```text
expected_entry  = current ask + modeled slippage
candidate_stop  = lowest low of the 3-bar pullback window - 1 tick
candidate_R     = expected_entry - candidate_stop
```

Skip if:

```text
candidate_R > 1.5 * ATR(14)
candidate_R < 0.5 * ATR(14)
candidate_R <= 0
```

On actual fill:

```text
actual_R = actual_entry_fill - stop_price
target   = actual_entry_fill + 1.5 * actual_R
```

Target rounded **DOWN** to nearest valid tick.

If `actual_R <= 0`, transition to `ERROR_HALTED`.

## B.7 Short entry rules

Exact mirror of long.

A short signal is valid only if all conditions are true:

1. `10:35:00 ET <= T_close <= 15:30:00 ET`
2. Most recently closed 60m RTH bar exists and is from the current
   session.
3. On that 60m bar:
   - `EMA50 < EMA200`
   - `60m close < EMA200`
4. On the 5m signal bar:
   - `5m close < 5m EMA200`
5. Pullback occurred within the last 3 closed 5m bars, including the
   signal bar:
   - at least one bar high touched or crossed above 5m EMA20 OR
     session VWAP.
6. Continuation trigger:
   - signal-bar close is strictly less than the low of the immediately
     preceding 5m bar.
7. No open position.
8. No more than 2 prior trades entered in the current RTH session.
9. No active no-trade condition.
10. Latency gates pass.

### Short stop and target

At decision time:

```text
expected_entry  = current bid - modeled slippage
candidate_stop  = highest high of the 3-bar pullback window + 1 tick
candidate_R     = candidate_stop - expected_entry
```

Skip if:

```text
candidate_R > 1.5 * ATR(14)
candidate_R < 0.5 * ATR(14)
candidate_R <= 0
```

On actual fill:

```text
actual_R = stop_price - actual_entry_fill
target   = actual_entry_fill - 1.5 * actual_R
```

Target rounded **UP** to nearest valid tick.

If `actual_R <= 0`, transition to `ERROR_HALTED`.

## B.8 No-trade conditions

No entry if any condition is active:

- outside 10:35–15:30 ET signal window
- inside scheduled news blackout
- position open within pre-news flatten window
- bid/ask spread > 2 ticks
- latest tick older than 3 seconds
- missing BBO
- locked or crossed book
- broker connection degraded
- exchange halt
- limit-up / limit-down
- clock drift > 250 ms
- signal calculation latency > 2 seconds
- signal-to-order submission latency > 3 seconds
- order-state machine not `FLAT`
- operational kill switch active

## B.9 News flatten

No position may be open at scheduled high-impact release time.

Flatten times:

- CPI, NFP, PPI, GDP, Retail Sales, ISM: flatten by T−12 minutes.
- FOMC rate decision: flatten by T−32 minutes.
- FOMC minutes: flatten by T−17 minutes.

If flatten fails before release time, transition to `ERROR_HALTED`.

## B.10 Forced session-end flatten

At 15:58:00 ET:

1. Halt new entries.
2. Keep protective stop active.
3. Submit market flatten order.
4. Confirm broker position is flat.
5. Cancel remaining OCO leg.
6. If flat confirmation fails, retry once.
7. If still not flat, transition to `ERROR_HALTED`.
8. If position flips or broker / internal mismatch occurs, transition
   to `ERROR_HALTED`.

Cancel-first is allowed only through documented broker-native atomic
flatten.

## B.11 v0.3 family rule

v0.3 may use the v0.2 OOS partition as clean validation only if v0.3
rules were registered (in the strategy registry, per §B.13) **before**
the v0.2 OOS query.

If v0.3 is designed after seeing v0.2 OOS results, that OOS is
contaminated and may be used only as a diagnostic comparison.

Final holdback remains binding family-level validation.

## B.12 Sign-off

| Field                | Value |
| -------------------- | ----- |
| Signed               | false |
| Director Sponsor     | DIR-01 |
| Risk Reviewer        | RISK-01 |
| Signed at ISO        | null |
| Commit hash          | null |
