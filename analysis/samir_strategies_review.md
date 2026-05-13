# Tom3.cs and Achour002.cs — Independent Review

Two NinjaTrader 8 C# strategies from `\\Mac\Home\Documents\Samir strategies\`.
This is my first-pass static analysis before discussing with codex.

---

## Tom3.cs — EMA-gap "breakout" strategy

### Stated intent (inferred from code)
When the gap between EMA(200) and EMA(20) widens past a threshold, enter in the
direction the price is currently on. Held until session close.

### Critical bugs

**1. EMArange2 is never initialized.**
```csharp
EMArange1 = 40;
EMArange1 = 70;   // typo — should be EMArange2 = 70
```
Both lines assign to `EMArange1`. `EMArange2` falls back to C# int default (0),
so the second threshold check `if (EMArange > EMArange2)` fires the moment the
EMAs are not perfectly equal — i.e. every single bar after warmup.

**2. The long/short branch can never go short.**
```csharp
if (EMArange > EMArange1) {
    if (Close[0] < EMA200[0]) Short = true;
    if (Close[0] > EMA200[0]) Long  = true;
}
...
if (EMArange > EMArange2) {
    if (Short && Long == true) EnterShort();
    else                       EnterLong();
}
```
`Short` and `Long` are mutually exclusive — `Close` can't be both above and
below `EMA200` simultaneously. The short branch requires BOTH to be true, which
never happens. **The strategy is effectively long-only**, regardless of trend.
Whenever the EMA gap exceeds `EMArange1`, it goes long.

**3. No stop loss, no profit target.**
`SetStopLoss` and `SetProfitTarget` are commented out. The only exit is
`IsExitOnSessionCloseStrategy` 180 s before session close. Every entry is held
all day. Drawdowns are unbounded intraday.

**4. Dead code.**
`RSI1`, `key2`, `BarsSinceKey1` are computed/declared but never read. `key1`
is set but its value is never branched on.

### What it actually does in practice
Whenever EMA(200)−EMA(20) exceeds 40 points (the only threshold that's set),
enter long with default sizing, hold until session close. No risk management.

---

## Achour002.cs — ATRTrailing flip + RSI filter

### Stated intent (inferred)
Catch flips in an ATRTrailing indicator on the primary chart, gate on RSI,
exit on opposite ATRTrailing flip on a 20-minute series (or RSI extreme).

### Critical bugs

**1. Hard stop is backwards.**
```csharp
if (Low[0] <= Position.AveragePrice - ATR1[0] * 10)
    ExitShort(0, 1, "", "");
```
This condition is "price has dropped 10 ATR below entry" — a long-position
drawdown event. But it calls `ExitShort()`, which closes a **short** position.

  - Long & price tanks → tries to close a short you don't have → no-op. **No
    stop protection for longs.**
  - Short & price tanks → closes your winning short → **realises a winner
    prematurely on adverse moves you'd want to keep.**

This is a destructive bug. The line should be `ExitLong()`, and there should
be a symmetric `ExitShort()` for `High[0] >= AvgPrice + ATR*10`.

**2. ATRTrailing variable numbering is inverted vs use.**
- `ATRTrailing1` runs on `Closes[1]` (the 20-min added series). Used **only**
  for exits.
- `ATRTrailing2` runs on `Close` (primary chart). Used **only** for entries.

Reading the code, you have to keep reminding yourself the numbers don't match
the role. Easy place to introduce a future bug.

**3. `Barssinenentry1` is a 20-minute counter.**
```csharp
if (Position.MarketPosition != MarketPosition.Flat && BarsInProgress == 1)
    Barssinenentry1++;
```
Only ticks on the 20-minute series. The exit gate `Barssinenentry1 > 2`
therefore requires ~60 minutes in-trade before signal-driven exits can fire.
Combined with the broken hard stop, **a losing long has no exit for the
first ~60 minutes**.

**4. Weak RSI filter.**
- Long entry: `RSI > RSI_Low + 15` → with `RSI_Low=30`, that's RSI > 45.
- Short entry: `RSI < RSI_High - 15` → RSI < 55.

RSI sits between 40 and 60 most of the time. This filter rejects almost
nothing.

**5. Operator-precedence footgun.**
```csharp
if ((Close[0] < ATRTrailing1.Lower[0] && ATRTrailing1.Lower[0] != 0
     || RSI1[0] < RSI_Low) && Barssinenentry1 > 2)
```
C# binds `&&` tighter than `||`, so this parses as
`((A && B) || C) && D`. That's probably what's intended, but it's fragile;
any future edit by someone who doesn't know the precedence rules will break
silently.

**6. Dead/unused code.**
`EMA10` is declared, never instantiated, never used (initialization is
commented out). `Stochastics1` same. Confusing.

---

## Cross-cutting issues (both strategies)

- **No position sizing** — both use default contract count via `EnterLong()`
  / `EnterShort()`. No `Quantity` parameter, no risk-per-trade scaling.
- **No daily loss cap** — neither has a circuit breaker.
- **No proper bracket** — neither submits stop+target as part of the entry.
- **Hardcoded magic numbers** — Tom3 has `200`, `20`, `14`, `3`, `180` baked
  in. Achour002 has `4, 10, 0.005`, `10`, etc., as ATRTrailing params with no
  rationale and no parameter exposure.
- **`Calculate.OnBarClose`** for both (good — avoids intra-bar repaint).
- **`SessionIterator` + `IsExitOnSessionCloseStrategy`** (good — flat at EOD).
- **`StartBehavior.WaitUntilFlat`** (good for live).

---

## Comparison to v0.2 (the Python strategy we already have)

| Feature                        | Tom3            | Achour002       | v0.2 (ours)          |
|--------------------------------|-----------------|-----------------|----------------------|
| Trend filter                   | EMA200 (1 TF)   | none            | EMA50/200 on 60 m    |
| Pullback entry                 | no              | flip-based      | yes (EMA20 / VWAP)   |
| ATR-based R sizing             | no              | no              | yes                  |
| Stop loss attached             | **no**          | **buggy**       | yes (bracket OSO)    |
| Profit target attached         | **no**          | no              | yes (1.5 R)          |
| Session window                 | EOD flat only   | EOD flat only   | 10:35–15:30 ET       |
| Daily loss cap                 | no              | no              | yes                  |
| Kill switch                    | no              | no              | yes                  |
| Tested                         | no              | no              | 242 unit tests       |

---

## Questions for codex

1. Are there nuances of NinjaTrader's `EnterLong()` / `ExitShort()` semantics
   that would make the apparent bugs above harmless (e.g. ExitShort being
   silently rerouted when flat-long)?
2. Is there any way the "Short && Long == true" branch in Tom3 could be hit in
   practice — e.g. multi-series timing — that I'm missing?
3. For Achour002's 20-minute exit gate, is the design ("wait at least 3 bars on
   the slow series before allowing trail/RSI exit") a recognised pattern, or is
   it just an artefact?
4. Would you port either of these strategies into the Path B Python framework,
   or treat them as reference material only?
