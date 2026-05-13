# NT8 Multi-Strategy Workflow — Portfolio Backtest & Live Deployment

Operating doc for running Tom3 + OvernightCounter + VariableTrend (and similar
portfolios) in NinjaTrader 8 on Parallels/macOS.

Documents root on this machine: `\\Mac\Home\Documents\NinjaTrader 8\`

---

## 1. Backtesting multiple strategies

### 1.1 What NT8 Strategy Analyzer actually supports

NT8 Strategy Analyzer is **single-strategy**. One run = one strategy script
against one instrument (or a basket of instruments for that same strategy).
There is no native "portfolio backtest" that loads Strategy A, B, C onto the
same account, shares P&L, and reports a combined equity curve.

Confirmed against the help guide:

- Strategy Analyzer overview lists "Basket testing multiple instruments" as a
  feature — this is one strategy run across many symbols, not many strategies.
  (`https://ninjatrader.com/support/helpguides/nt8/strategy_analyzer.htm`)
- The Optimizer iterates parameters of the **selected** strategy. No
  multi-script slot exists in the run dialog.
- Strategies tab on Control Center (live) does support many strategies on one
  account simultaneously — but that is a live-trading feature, not a backtest.

Implication: there is no "press one button and see combined Tom3 +
OvernightCounter + VariableTrend equity curve" in NT8. You must run each
strategy individually and combine offline.

### 1.2 Offline combination workflow (recommended)

For each strategy in the portfolio:

1. Open Strategy Analyzer (New > Strategy Analyzer, or `Ctrl+F8`).
2. Pick instrument (e.g. `NQ 06-26` continuous contract or `NQ ##-##`).
3. Pick date range — **use the identical range for every strategy** so daily
   P&L series line up.
4. Pick data type / bar settings — must match the strategy's intended chart
   (e.g. 5-min, regular session, etc.). Mismatches here are the #1 source of
   "backtest doesn't look like live."
5. Set commissions / slippage in the strategy parameters or via the analyzer's
   commission template. Be consistent across strategies.
6. Right-click the strategy row > **Backtest** (or run the optimization with
   a single parameter set).
7. Export the trade list (see section 2) to CSV.

Then combine offline:

- Load each CSV into pandas (see `C:\Users\MAC\AlgoTrading\analysis\
  portfolio_analysis.py` — already does this pattern).
- Resample each trade list to **daily realized P&L** keyed on the trade exit
  date (NT8's `Time` column on the Trades tab is the exit time).
- Sum per-day across strategies = portfolio daily P&L.
- Compute combined max drawdown on the **cumulative sum**, not the sum of
  individual drawdowns (drawdowns are not additive — that overstates risk).

Important caveats with this approach:

- **No shared account constraint.** If Tom3 and OvernightCounter both go long
  NQ on the same bar, the combined sim doesn't know contracts stack. See
  section 5.
- **No portfolio-level risk wrapper.** PortfolioTrail.cs's daily-trail behaviour
  cannot be reproduced offline without re-simulating order timing.
- **Margin/buying-power** is not modeled at all in the offline sum.

For most signal-research questions (does adding strategy X improve combined
Sharpe?) the offline sum is good enough. For prop-firm sizing / drawdown rule
compliance, you must paper-trade the full portfolio in Sim101 (section 3).

### 1.3 Walk-forward and parameter sets

If each strategy has its own optimized parameter set, freeze them before
combining. Don't optimize each strategy on the same window you measure
combined performance on — that's the classic in-sample/out-of-sample leak.

---

## 2. Exporting daily P&L from one Strategy Analyzer run

After a backtest completes, the bottom pane of Strategy Analyzer shows the
Performance report. Tabs available:

- **Summary** — aggregate stats only, not useful for daily series.
- **Trades** — one row per round-trip. **This is what you export.**
- **Executions** — one row per fill (entry and exit are separate rows).
- **Periods** — built-in daily/weekly/monthly breakdown.
- **Graphs** — equity curve visualization.
- **Orders** — order-level data.

### 2.1 Export path

1. Click the **Trades** tab in the performance pane.
2. Right-click anywhere in the trade grid.
3. Choose **Export...** from the context menu.
4. Pick CSV or Excel format. Save to a known folder, e.g.
   `\\Mac\Home\Documents\NinjaTrader 8\backtest_exports\<strategy>_<daterange>.csv`.

The Trades export includes: Trade #, Instrument, Account, Strategy, Market pos,
Quantity, Entry/Exit price, Entry/Exit time, Entry/Exit name (the `signalName`
arg from `EnterLong("name")` / `ExitLong("name")` — this is your **exit
reason**), Profit, Cum. profit, MAE, MFE, ETD, Bars.

### 2.2 Building daily P&L from the Trades export

```python
import pandas as pd
df = pd.read_csv("Tom3_2024.csv")
df["ExitDate"] = pd.to_datetime(df["Exit time"]).dt.date
daily = df.groupby("ExitDate")["Profit"].sum()
```

Repeat per strategy, then `pd.concat(axis=1).fillna(0).sum(axis=1)` for the
combined daily series.

### 2.3 Alternative: Periods tab

The Periods display has a built-in "Daily" breakdown. Right-click > Export
also works there. Slightly fewer columns but no aggregation needed. Use this
if you only want daily totals and don't care about per-trade exit reasons.

### 2.4 Note on commissions

NT8 reports **Profit** net of commission only if the strategy or analyzer has
commissions configured. Verify by spot-checking one trade — `(exit-entry) *
multiplier - commission`. If commissions are zero in the export, your daily
P&L is gross.

---

## 3. Live deployment — running 3 strategies in parallel

### 3.1 Two ways to attach a strategy

**A. Chart-based (Strategies tab on a chart window)**

- Open chart for the instrument > Strategies icon > Add the strategy.
- Pros: visual confirmation, easy parameter tweaks, indicator-style debugging.
- Cons: strategy is tied to that chart's bar series. Closing the chart kills
  the strategy. One chart per strategy = N charts open for N strategies.

**B. Control Center > Strategies tab (the "headless" way)**

- Control Center > Strategies tab > right-click > **New Strategy...**
- Pick strategy, instrument, account, parameters.
- Pros: not tied to any chart window. Survives chart closes. All running
  strategies visible in one grid.
- Cons: no chart to eyeball signals on. (You can still open a chart of the
  instrument separately for visualization.)

Recommended for portfolio operation: **Control Center Strategies tab**. Open
one chart per instrument for visualization, but instantiate the strategies
from the Strategies tab so they're independent of the chart windows.

### 3.2 Workspace organization

Save a workspace named e.g. `Live_Portfolio.xml` containing:

- Control Center.
- One chart per instrument being traded (NQ in this scenario).
- The Strategies tab pre-populated. NT8 persists running strategies in the
  workspace, so reopening it restores them.

If you trade multiple instruments, group them: one workspace per portfolio,
not one strategy per workspace.

### 3.3 Visual status colors on the Strategies tab

- Green checkbox = strategy running and synced.
- Orange = syncing strategy position to account (transitional, usually after
  enable).
- Black = disabled / stopped.

### 3.4 Same-instrument concurrency

NT8 allows multiple strategy instances on the same instrument and same
account. Each one tracks **its own** strategy position (positions are tracked
per strategy instance, not per account, unless you call `SetOrderQuantity =
OrderQuantity.ByStrategy`, which is the default). The account-level position
is the algebraic sum across all running strategies.

This is exactly the stacking case in section 5.

### 3.5 Sync strategies

Right-click in Strategies tab > **Synchronize All Strategies** = "Aggregate
all strategy positions and sync aggregate value to the accounts position."
Run this once after restarting NT8 if a strategy was holding a position when
you shut down, otherwise NT8 may not know about the open position.

### 3.6 Connection considerations

Live and Sim101 share the same NT8 instance. If you're testing the portfolio
on Sim101 while a different account is live, double-check the **Account**
dropdown on each strategy when adding it. Misrouting Tom3 to a live account
during paper validation is the kind of mistake that ends careers.

---

## 4. Account-level risk wrapper (PortfolioTrail)

File: `\\Mac\Home\Documents\Samir strategies\samir 700 dollar strategieen\PortfolioTrail.cs`
(Jacob Amaral pattern, YouTube channel: Jacob Amaral).

### 4.1 What it does

It is a **strategy** in name only — it does not place its own entry orders.
It runs on a chart/Strategies-tab slot like any other strategy, reads the
**account-level** realized + unrealized P&L on every bar:

```csharp
double unrealizeddaypnl = Account.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);
double realizedpnl       = Account.Get(AccountItem.RealizedProfitLoss,   Currency.UsDollar);
double daypnl            = unrealizeddaypnl + realizedpnl;
```

Logic:

1. If `daypnl >= dailyTrailTarget` (e.g. $1000), activate the trail.
2. Track `trailWatermark` — the high-water mark of daypnl since activation.
3. If `daypnl <= trailWatermark - trailWatermark * (dailyTrailStop / 100)`
   (e.g. 25% giveback), close every futures position on the account:

```csharp
foreach (Position pos in Account.Positions) {
    if (pos.Instrument.MasterInstrument.InstrumentType == InstrumentType.Future) {
        pos.Close("TrailStop");
    }
}
```

4. Reset watermark on first or last bar of session.

### 4.2 How it sits over the portfolio

PortfolioTrail is **agnostic** to which strategies are open. Because it reads
`Account.Get(...)` it sees the **summed** P&L of Tom3 + OvernightCounter +
VariableTrend (and anything else on that account). When it triggers, the
`foreach pos in Account.Positions` flatten will close positions across **all**
strategies, regardless of which strategy opened them.

This is exactly the right behavior for a daily-trail risk rule. It is also a
sharp knife: if PortfolioTrail flattens, the individual strategies will see
their positions disappear "out from under them" and may re-enter on the next
bar. Options to prevent re-entry:

- Set a session-level flag (separate strategy or via `Account.Flatten` then
  disable the other strategies via the API — there is no clean built-in way).
- Common workaround: PortfolioTrail also calls `Account.CancelAllOrders` and
  then leaves you to manually disable strategies. The reference version in
  the file does **not** do that — review and harden before live use.

### 4.3 Deployment

Add PortfolioTrail like any other strategy on the Strategies tab, **same
account** as the trading strategies. Bar series for PortfolioTrail can be
anything tick-rate-reasonable (1-minute NQ is fine) — it only needs OnBarUpdate
ticks to re-check P&L. Make sure `BarsRequiredToTrade` is small (the file uses
20) so it goes active quickly.

`State.Historical` short-circuits the logic (`return` early), so
PortfolioTrail is a **no-op in Strategy Analyzer backtests**. To simulate
its effect offline, you must re-implement the trail in Python over the
combined daily series.

### 4.4 Variants in the same folder

- `PortfolioTrailApex.cs` — Apex-specific tweaks.
- `PortfolioTrailStandard.cs` / `...sim103.cs` / `...playback.cs` — account-name
  variants. Look at each before picking; they differ in flatten behaviour and
  session-reset details.

---

## 5. Stacked exposure — the multi-strategy long-NQ trap

### 5.1 The problem

Tom3, OvernightCounter, and VariableTrend each "think" they trade 1 NQ
contract. If all three signal long at 09:35, the **account** is long 3 NQ —
~$66k notional per contract times 3 = ~$200k notional on a single instrument
correlated by definition.

NT8 does **not** warn you. Each strategy tracks its own strategy position;
the account aggregates them silently. PortfolioTrail will see the combined
P&L swing 3x faster than any single strategy expects, and its trail-stop
calibration (set on single-strategy assumptions) may be wrong.

### 5.2 Detecting it live

- **Control Center > Positions tab**: shows account-level position per
  instrument. If it reads "NQ 06-26: Long 3" while three strategies each
  show Long 1 on the Strategies tab, you are stacked.
- **Strategies tab**: expand to view per-strategy position. Sum manually and
  compare to Positions tab.
- **Programmatic check** (e.g. inside PortfolioTrail or a sentinel strategy):

```csharp
foreach (Position pos in Account.Positions) {
    if (Math.Abs(pos.Quantity) > maxAllowedContracts) {
        Log($"STACKED EXPOSURE: {pos.Instrument.FullName} = {pos.Quantity}",
            LogLevel.Warning);
        // optional: pos.Close("StackGuard");
    }
}
```

  This is the cleanest path — add a stack-guard rule next to PortfolioTrail.

### 5.3 Detecting it post-hoc (from backtest CSV exports)

After exporting each strategy's Trades CSV per section 2:

```python
import pandas as pd
def load(s): 
    d = pd.read_csv(f"{s}.csv", parse_dates=["Entry time","Exit time"])
    d["strategy"] = s
    return d
trades = pd.concat([load(s) for s in ["Tom3","OvernightCounter","VariableTrend"]])
# Build a minute-by-minute position series per strategy, then sum
# Find every minute where summed_abs_pos > 1
```

The user's `portfolio_analysis.py` in `C:\Users\MAC\AlgoTrading\analysis\`
already has scaffolding for this — extend it to emit a stacking-incidents
report.

### 5.4 Mitigation options

1. **Position-size scaling.** Halve contracts on each strategy if all three
   are long-only NQ. Crude but works.
2. **Sentinel strategy.** A small NT8 strategy that runs alongside the
   portfolio, polls `Account.Positions[NQ].Quantity`, and if it exceeds the
   stacking cap, force-flattens the **last** entry (hardest part: identifying
   which strategy is "last"; in practice, flatten everything and disable
   re-entry until next session).
3. **Master/slave coordination.** A shared file or named-pipe between the
   strategies where each one checks "is the desk already long NQ?" before
   entering. Higher effort, cleaner result.
4. **Accept it, but resize.** If correlation across the three signals is low
   enough, stacking is a feature, not a bug — but size accordingly and
   recalibrate PortfolioTrail's `dailyTrailTarget` / `dailyTrailStop` for the
   3x leverage case.

For prop-firm accounts (Apex/TopStep/etc.) where max-contracts and trailing
drawdown rules are hard limits, option 1 or 2 is mandatory. Option 4 is for
own-capital traders.

---

## Appendix — Quick checklist before going live with the portfolio

- [ ] Each strategy backtested on identical date range, identical instrument,
      identical commission/slippage assumptions.
- [ ] Daily P&L exports combined offline, combined drawdown and Sharpe
      computed.
- [ ] Stacking analysis run: how often are >=2 strategies long the same
      instrument simultaneously? What's the worst-case combined contract
      count?
- [ ] PortfolioTrail re-simulated in Python over the combined series — does
      it ever trigger? How much does it cost vs. save?
- [ ] Workspace `Live_Portfolio.xml` saved with Control Center, NQ chart,
      and Strategies tab populated (each strategy + PortfolioTrail + any
      stack-guard sentinel), all routed to **Sim101** first.
- [ ] One full session in Sim101 with the live portfolio. Eyeball the
      Positions tab during overlap windows.
- [ ] Re-verify Account dropdown on every strategy before flipping to the
      funded account.
- [ ] PortfolioTrail's `dailyTrailTarget` and `dailyTrailStop` calibrated for
      the combined exposure, not for any single strategy.

---

Last updated: 2026-05-14.
