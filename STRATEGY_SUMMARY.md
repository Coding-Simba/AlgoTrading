# AlgoTrading — Full Strategy & Status

_Last updated: 2026-05-14_

## Goal

Run an automated futures portfolio on the **Tradeify Lightning Funded 100K** prop account, trading NQ micros (MNQ), built around Samir's existing Tom3 strategy plus complementary low-correlation strategies for diversification — wrapped in a compliance + risk guard sized for the prop firm's rules.

## The portfolio

### Live trader: Tom3

Samir's flagship strategy. EMA-gap "breakout" on NQ:
- `EMA(20)` vs `EMA(200)` on 1-minute bars
- When the gap exceeds threshold, enter in the direction price is on relative to EMA(200)
- Effectively long-only due to a preserved direction-selection idiom in the code
- Hold to session close (~3 minutes before)
- 1048 trades over 2019–2026, **$674,920 net on 1× NQ**, **$67,492 on 1× MNQ**
- 7-year MaxDD: -$66,940 NQ = **-$6,694 MNQ**
- Worst single day: **-$2,332.50 MNQ** (0 days below -$2,500)
- Win rate: 57.3%, PF 1.52, Ret/DD 10.08×

### Complementary strategies (Tradeify-allowed concurrency pending)

Three uncorrelated NQ strategies from the WeTrade Labs "Lightning Funded" commercial pack:

| Strategy | Timeframe | Indicators | Own net (7yr, MNQ) | MaxDD (MNQ) | Corr to Tom3 | Tom3 worst-20 cushion |
|---|---|---|---:|---:|---:|---:|
| **VariableTrend** | 70-min ETH | VMA(9,9) crossover, $1K stop | $18,975 | -$4,608 | **−0.006** | **+$5,326** ✓ |
| **BlueLightning** | 10-min RTH | EMA200 + SMA20 + MACD + Bollinger + Momentum | $13,391 | -$1,691 | +0.106 | -$525 ⚠ |
| **NQPivots** | 1-min RTH | Camarilla pivots + EMA + ATR | $8,735 | -$1,973 | -0.043 | +$594 (5/0 pos/neg) ✓ |

### Rejected strategies (don't deploy)

- **MomentumNQ** — Backtest shows -$388 over 7 years (PF 0.90, losing). Workbook's claimed +$119K was either over-fitted to the 2022-2025 chop period or used different parameters. Skip permanently.
- **OvernightCounter, EarlyNight** — Both depend on `NinjaTrader.Custom.Strategies.StratGenV2.DetectPatternsV2`, which isn't in the WeTrade Labs `.cs` pack. Blocked until that helper is sourced (ask WeTrade Labs support).

### The compliance + risk wrapper: TradeifyGuard

Custom account-level NinjaScript strategy (written for this project) that monitors the prop account and enforces four rules:

1. **Daily Loss Guard** — flatten + halt if today's realized + unrealized P&L drops below -$2,000 ($500 buffer below Tradeify's -$2,500 soft daily limit).
2. **Trailing DD Guard** — flatten + halt if account equity drops more than $3,500 below running peak ($500 buffer below Tradeify's $4,000 hard trailing max).
3. **Cross-instrument prohibition** — if account holds both MNQ and NQ, auto-flatten NQ (Tradeify forbids minis + micros simultaneously).
4. **Same-symbol direction lock** — cancel any working entry order that would create an opposing position vs current account direction. (Market orders fill before this fires; covers limits/stops.)

Halt clears at next session start. Includes public static API `TradeifyGuard.IsEntryAllowed(symbol, direction)` for strategies that want to opt into pre-trade gating.

## Portfolio performance (combo backtest, 7 years on YOUR NT8 numbers)

Per `analysis/portfolio_5strat_results.md`:

| Configuration | Net (MNQ) | MaxDD (MNQ) | Ret/DD | Best for |
|---|---:|---:|---:|---|
| **Tom3 alone** | $67,492 | -$6,694 | 10.08× | Path A baseline (only safe option if Tradeify rejects concurrent strategies) |
| Tom3 + VariableTrend | $86,467 | -$5,852 | 14.77× | Two-strategy minimum |
| Tom3 + VT + NQPivots | $95,202 | -$5,635 | 16.90× | Conservative — both extras have positive worst-day cushion |
| **Tom3 + VT + BL + NQPivots** | **$108,593** | **-$5,649** | **19.22×** | Maximum return (BL has neg cushion on Tom3 worst-20 but doesn't materially raise worst day) |

The chop years 2021 and 2023 — where Tom3 alone underperforms — are where the portfolio adds the most:

| Year | Tom3 alone | Tom3 + VT + BL + NQP | Δ |
|---|---:|---:|---:|
| **2021 (chop)** | $1,887 | **$9,884** | **+$7,997 (5×)** |
| **2023 (chop)** | $2,232 | $4,886 | +$2,654 (2×) |
| Other years | varies | combined adds 30-100% | |

## Critical open question

**Does Tradeify allow simultaneous opposing-direction orders on the same instrument across multiple automated strategy instances on one account?**

Background: futures broker auto-nets positions, so the account never *holds* opposing positions. But Tradeify's order blotter does briefly show overlapping long+short tickets when (e.g.) Tom3 enters long while NQPivots's bearish pivot fires short within the same minute.

Tradeify's published rule says "no long + short on same instrument at same time" — ambiguous on the netted-futures case. The answer determines whether we run Path B (all 4 strategies concurrent) or Path C (sequential coordination via the guard's IsEntryAllowed API).

**Email Tradeify support before going live.** Until clarified, deploy only Tom3 (Path A).

## Current deployment status

```
GUARD: TradeifyGuard.cs — deployed, awaiting Sim101 verification
TRADERS (deployed in NT8, all NQ-Mini-spec):
  Tom3.cs                       ← LIVE-READY (Path A)
  VariableTrend.cs              ← compile-ready, deploy pending Tradeify confirm
  BlueLightning.cs              ← compile-ready, deploy pending Tradeify confirm
  NQPivots.cs                   ← compile-ready, deploy pending Tradeify confirm

VARIANTS (testing only, NOT FOR LIVE):
  Tom3Surgical.cs (per-trade tactical exits — proven to hurt edge)
  Tom3Trail.cs (currency trailing stop — proven to hurt edge)
  Tom3LossGuard.cs (PureShortLongBlock variant)
  Walid1.cs (entry-permission filters)

BLOCKED ON DEPENDENCY (StratGenV2.DetectPatternsV2):
  OvernightCounter.cs
  EarlyNight.cs

REJECTED:
  MomentumNQ.cs (unprofitable on your data, PF 0.90)
```

## Path forward

### Phase 1: Sim verification (this week)
1. Compile NT8 (F5) and verify all strategies build cleanly
2. Deploy `Tom3 + TradeifyGuard` to Sim101 only
3. Run 5-10 trading days
4. Verify guard fires correctly, account stays within Tradeify thresholds

### Phase 2: Tradeify support email (parallel to Phase 1)
1. Send the long+short clarification question (template in `analysis/tom3_plus_VT_results.md`)
2. Receive answer
3. If "yes" → Path B (4 concurrent strategies); if "no" → Path C (coordinated via IsEntryAllowed)

### Phase 3: Live deployment
1. Migrate the validated Sim setup to the real Tradeify Funded 100K account
2. Monitor daily; expect 1 wrapper trigger every 1-3 months historically

### Phase 4: StratGenV2 hunt (low priority)
1. Email WeTrade Labs support asking for the `DetectPatternsV2` helper
2. If found, deploy OvernightCounter and EarlyNight — both projected as strong portfolio additions per their workbook stats

## Files in this repo

```
nt8-strategies/
  TradeifyGuard.cs            ← our compliance + risk wrapper
  Tom3.cs, Tom3Surgical.cs, Tom3Trail.cs, Tom3LossGuard.cs, Walid1.cs
  VariableTrend.cs, BlueLightning.cs, NQPivots.cs   (subject to push-permission)
  blocked-deps/
    OvernightCounter.cs, EarlyNight.cs              (subject to push-permission)
  INSTALL.md

analysis/
  STRATEGY_SUMMARY.md         ← this file
  combo_analysis.py           ← portfolio combine pipeline (Python)
  portfolio_v2.py             ← workbook XML parser
  read_dashboard.py           ← xlsm sheet dump
  map_strategies.py           ← .cs file classifier
  portfolio_5strat_results.md ← final combo analysis
  tom3_plus_VT_results.md     ← 2-strategy combo baseline
  tom3_alone_results.md       ← single-strategy baseline
  dashboard_dump.md           ← key workbook sheets
  strategy_map.md             ← workbook → .cs file map
  nt8_multi_strategy_workflow.md ← NT8 multi-bot workflow doc
  samir_strategies_review.md  ← static review of Tom3 and Achour002
  codex_*.md                  ← codex prompt prep docs

  trades-csv/                 (subject to push-permission)
    tom3 trades 2019-2026.csv
    variabletrend, bluelightning, nqpivots, momentumnq exports
```

## Glossary

- **MaxDD**: maximum cumulative drawdown from peak equity (over the full period)
- **Ret/DD**: net profit divided by absolute MaxDD; higher = better risk-adjusted return
- **Worst-day cushion**: P&L the candidate made/lost on the 20 days Tom3 lost the most
- **Tradeify trailing max DD**: hard liquidation threshold, $4,000 from running peak (locked at $100,100 once profit exceeds it)
- **Tradeify daily loss limit**: soft warning, $2,500 today's PnL — NOT an automatic stop, can be exceeded by slippage
- **EOD trailing**: drawdown is evaluated at session close (not intraday max)
- **DD-overlap days**: number of days all strategies in a portfolio are simultaneously underwater; lower = better diversified
