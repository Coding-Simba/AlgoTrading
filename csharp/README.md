# AlgoTrading — C# / NinjaScript port

This directory holds the C# port of the Python `src/algotrading/` package.

**Branch:** `csharp-port` (forked from `claude/release-signoff-v1.4-r1-RfVcm`).
The original Python codebase remains untouched on its branch.

## Layout

```
csharp/
  AddOns/                 Library code, mirrors src/algotrading/<module>/
    Domain/               Tick, Bar, BBOQuote, EntrySide
    Calendar/             Session calendar
    Bars/                 Bar builder
    Indicators/           EMA, VWAP, ATR
    FillModel/            Fill model + rate-sheet cost
    Orders/               Order state machine + execution lifecycle + flatten
    Broker/               BrokerOrder/Fill types, IBrokerAdapter, refusing stubs
    Baselines/            Random / drift-matched / reversed runners
    Monitoring/           Latency + clock-drift
    Contamination/        Contamination log + enforcement
    Registry/             Strategy registry
    Backtest/             Backtest engine + gates
    Governance/           Phase gates, risk limits, signoff matrix
    Configs/              YAML config record types (deserialization targets)
  Strategies/             NinjaScript Strategy classes (consumers of AddOns)
  Tests/                  xUnit test ports of tests/
  scripts/                Deployment scripts (Deploy-To-NT8.ps1)
```

## Target framework

NinjaTrader 8 compiles `.cs` files placed under
`%USERPROFILE%\Documents\NinjaTrader 8\bin\Custom\` into a single assembly
(`NinjaTrader.Custom.dll`). The compile target is **.NET Framework 4.8**
with **C# 7.3** language features. No records, no `init`-only setters,
no target-typed `new()`. Constructors + readonly properties are the
idiom.

## Deployment

Source of truth lives in this `csharp/` folder. NinjaTrader 8 only sees
files inside its `Documents\NinjaTrader 8\bin\Custom\` tree. Two
options:

1. **Manual copy:** copy `csharp/AddOns/**/*.cs` into
   `Documents\NinjaTrader 8\bin\Custom\AddOns\AlgoTrading\` and
   `csharp/Strategies/**/*.cs` into
   `Documents\NinjaTrader 8\bin\Custom\Strategies\`. Then in NT8:
   *Tools -> Compile* (or F5).
2. **Script:** `scripts/Deploy-To-NT8.ps1` (added later) copies the
   tree and triggers compile.

Don't edit files in `bin/Custom` directly — those are deployed
artifacts. All edits go in `csharp/` first.

## Namespace convention

- Library code: `AlgoTrading.<Module>` (e.g., `AlgoTrading.Domain`,
  `AlgoTrading.Calendar`).
- NinjaScript strategies: must be `NinjaTrader.NinjaScript.Strategies`
  (NT8 requirement for discovery).

## What is intentionally NOT ported

- `src/algotrading/__main__.py`, `cli.py`: Python-only entry points.
- `tests/test_sprint1_freeze.py`: enforces a *Python source freeze*; the
  C# port is itself a freeze violation in spirit, but only on the new
  branch. The original branch's freeze is unaffected.
- `pyproject.toml`: replaced by NT8's compile pipeline.

## What changes vs. the Python design

- `LiveBrokerAdapter` / `TradovateAdapter` remain refusing stubs,
  preserving the gate-protected refusal semantics. They are not the
  primary execution path for the C# port.
- A new `NinjaBrokerAdapter` (under `AddOns/Broker/`) wraps NT8's order
  entry surface (`Strategy.EnterLong`, `Strategy.SubmitOrderUnmanaged`,
  etc.) and is what the running strategy actually uses.
- `bars/`, `calendar/`, `indicators/` are kept in the library for
  parity with the Python tests, but the NinjaScript Strategy wrapper
  may bypass them in favour of NT8's native `BarsArray`, `Session`,
  `EMA()`, `VWAP()`, `ATR()` for live use.
