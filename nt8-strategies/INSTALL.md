# NT8 Strategies — Install on a New PC

Four NinjaScript strategies for NinjaTrader 8 backtesting/sim:

| File | Class / Display | Purpose |
|---|---|---|
| `Tom3.cs` | `Tom3` / **Tom3** | Samir's original. EMA-gap "breakout" with the well-known direction-selection bug preserved. No risk wrappers. Reference / baseline. |
| `Tom3Trail.cs` | `Tom3Trail` / **Tom3 Trail** | Tom3 entry preserved + delayed currency trailing stop, catastrophe stop, optional take-profit, prevent-reentry-same-session. |
| `Tom3LossGuard.cs` | `Tom3LossGuard` / **Tom3 Loss Guard** | Tom3 entry preserved + `UsePureShortLongBlock` to skip the suspicious `Short=true, Long=false` forced-long case (Tom3's worst losers). Optional narrow emergency exit. |
| `Walid1.cs` | `Walid1` / **Walid 1** | Tom3 entry preserved + entry-permission filters only: HTF trend, ATR regime, opening range, Sunday Globex skip, optional catastrophe stop. **No active in-trade exits beyond NT8 session-close.** |

All four preserve Tom3's original direction-selection idiom intentionally. None of them "fix" the bug.

---

## Install steps on a new NT8 PC

1. Install NinjaTrader 8 (8.1.6+ recommended) on the target machine.

2. Launch NT8 once so it creates the user data folder (`Documents\NinjaTrader 8\`).

3. **Quit NT8 fully** (right-click tray icon → Exit; wait for the process to disappear from Task Manager).

4. Copy all four `.cs` files into:
   ```
   Documents\NinjaTrader 8\bin\Custom\Strategies\
   ```

5. Open NT8's csproj at:
   ```
   Documents\NinjaTrader 8\bin\Custom\NinjaTrader.Custom.csproj
   ```

   Check the `<EnableDefaultCompileItems>` property:

   - **If it is `true` (or missing)**: nothing else to do — NT8 will auto-include the new files.
   - **If it is `false`**: add these four lines to the `<ItemGroup>` that already contains `<Compile Include="Strategies\@Strategy.cs" />`:
     ```xml
     <Compile Include="Strategies\Tom3.cs" />
     <Compile Include="Strategies\Tom3LossGuard.cs" />
     <Compile Include="Strategies\Tom3Trail.cs" />
     <Compile Include="Strategies\Walid1.cs" />
     ```

6. Start NT8. Open **New → NinjaScript Editor**. Press **F5** to compile. After "Build succeeded", all four strategies appear in the Strategy Analyzer dropdown and the chart Strategies dialog.

If F5 throws `CS0579` duplicate-attribute errors about `resources.cs`, that's an unrelated NT8/MSBuild build-cache issue (it can happen on Parallels-shared Documents folders). Fix: quit NT8, delete `bin\Custom\obj\` and `bin\Custom\bin\` entirely, restart NT8.

---

## Default test parameters

Each strategy ships with the test defaults Samir specified. Quick reference:

### Tom3 (baseline only — don't ship to live)
```
EMArange1 = 40
EMArange2 = 70
```
No stops, no targets. Held to session close. Use only for backtest baseline.

### Tom3 Trail (first test)
```
EMArange1 = 40
EMArange2 = 70
PreventReentrySameSession = true
UseDelayedTrailingStop = true
TrailingActivationCurrency = 5000
TrailingStopCurrency = 4000
UseCatastropheStop = true
CatastropheStopCurrency = 20000
UseLargeTakeProfit = false
```
Trailing sweep: `(5000, 4000) → (7500, 4000) → (5000, 5000) → (7500, 5000) → (10000, 4000)`.

### Tom3 Loss Guard (first test)
```
EMArange1 = 40
EMArange2 = 70
UsePureShortLongBlock = true
BlockedSetupSkipsWholeSession = false
UseCurrentDirectionLongValidation = false
UseNeverWorkedEmergencyExit = false
```
If Test 1 doesn't beat Tom3 net, retry with `BlockedSetupSkipsWholeSession = true`.

### Walid 1 (baseline — all filters off)
```
EMArange1 = 40
EMArange2 = 70
PreventReentrySameSession = false   # ← set false for true Tom3-equivalent baseline
UseHigherTimeframeTrendFilter = false
UseATRRegimeFilter = false
UseOpeningRangeConfirmation = false
SkipSundayGlobex = false
UseCatastropheStopCurrency = false
```
Then enable one filter per test. See per-test parameter combinations in your test plan.

---

## Backtest comparison protocol

For any meaningful comparison between strategies, hold these CONSTANT across all backtests:
- Instrument (e.g. NQ 06-26)
- Date range
- Timeframe (1 Minute)
- Slippage
- Commission
- Trading hours template
- "Break at EOD" setting

Vary only the strategy and its parameters.
