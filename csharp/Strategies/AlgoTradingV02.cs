// AlgoTrading v0.2 — NinjaScript Strategy wrapper
//
// Consumes the C#-ported library under csharp/AddOns/ to produce v0.2
// entry signals (Appendix B §B.7) and apply the §B.8 no-trade gating.
// This file lives at bin/Custom/Strategies/ in the user's NinjaTrader 8
// install — see csharp/scripts/Deploy-To-NT8.ps1.
//
// IMPORTANT — sim only at the moment:
//   - Default order size is 1 contract.
//   - Strategy is intended for Sim101 / NT Brokerage demo. Do not run on
//     a funded account until paper soak + Appendix F process is done.
//   - Bracket exits use SetStopLoss + SetProfitTarget (managed approach).
//
// What is NOT yet wired (deliberately, per parity with Python):
//   - News blackout windows (need an external calendar feed).
//   - Pre-news flatten window.
//   - Clock-drift, signal-latency, order-latency monitors.
//   - Locked/crossed book, exchange halt, limit up/down feeds.
//   The corresponding NoTradeReason flags default to "off" until those
//   inputs are plumbed.

#region Using declarations
using System;
using System.Collections.Generic;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;
using AlgoTrading.Domain;
using AlgoTrading.Indicators;
using AlgoTrading.StrategyV02;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class AlgoTradingV02 : Strategy
    {
        // MES instrument constants (MES tick size = 0.25 index points).
        private const double TickSize_Indices = 0.25;

        // Strategy parameters (configurable from the NT UI).
        private int contractsPerEntry = 1;
        private int slippageTicks = 1;
        private int atrPeriod = 14;
        private int emaShortPeriod = 20;
        private int emaLongPeriod = 200;
        private int emaTrendShort = 50;
        private int emaTrendLong = 200;

        // Strategy state.
        private SessionCounters sessionCounters;
        private DateTime currentSessionDate = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                          = "v0.2 long/short on MES with 60m trend filter, 5m pullback entry, ATR-bounded R, 1.5R target. Port of the Python AlgoTrading framework.";
                Name                                 = "AlgoTradingV02";
                Calculate                            = Calculate.OnBarClose;
                EntriesPerDirection                  = 1;
                EntryHandling                        = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy         = true;
                ExitOnSessionCloseSeconds            = 120; // 15:58 ET-ish forced flatten.
                IsFillLimitOnTouch                   = false;
                MaximumBarsLookBack                  = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                  = OrderFillResolution.Standard;
                Slippage                             = 0;
                StartBehavior                        = StartBehavior.WaitUntilFlat;
                TimeInForce                          = TimeInForce.Gtc;
                TraceOrders                          = false;
                RealtimeErrorHandling                = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                   = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                  = emaLongPeriod + 50; // 250 bars warm-up.
                IsInstantiatedOnEachOptimizationIteration = true;
            }
            else if (State == State.Configure)
            {
                // Add a 60m secondary bars series for the trend filter.
                AddDataSeries(BarsPeriodType.Minute, 60);
            }
            else if (State == State.DataLoaded)
            {
                sessionCounters = new SessionCounters();
            }
        }

        protected override void OnBarUpdate()
        {
            // Only act on the primary (5m) series, on bar close.
            if (BarsInProgress != 0) return;
            if (CurrentBar < BarsRequiredToTrade) return;
            if (CurrentBars[1] < emaTrendLong) return; // 60m must be warm enough.

            // Reset session counters on new ET trading day.
            DateTime barTimeEt = ToEasternTime(Time[0]);
            DateTime barDate = barTimeEt.Date;
            if (barDate != currentSessionDate)
            {
                currentSessionDate = barDate;
                sessionCounters = new SessionCounters();
            }

            // Quick gate: are we even allowed to look at signals?
            if (Position.MarketPosition != MarketPosition.Flat) return;
            if (!sessionCounters.CanEnter()) return;

            // Build the rolling 5m window in oldest->newest order.
            int n = Math.Min(CurrentBar + 1, 250);
            var bars5m = new List<Bar5m>(n);
            var closes5 = new List<double>(n);
            var highs5 = new List<double>(n);
            var lows5 = new List<double>(n);
            var volumes5 = new List<double>(n);
            for (int btsIdx = n - 1; btsIdx >= 0; btsIdx--)
            {
                int hT = ToTicks(Highs[0][btsIdx]);
                int lT = ToTicks(Lows[0][btsIdx]);
                int cT = ToTicks(Closes[0][btsIdx]);
                bars5m.Add(new Bar5m(hT, lT, cT));
                closes5.Add(Closes[0][btsIdx] / TickSize_Indices);
                highs5.Add(Highs[0][btsIdx] / TickSize_Indices);
                lows5.Add(Lows[0][btsIdx] / TickSize_Indices);
                volumes5.Add(Volumes[0][btsIdx]);
            }

            // 5m indicators (computed on a tick-unit basis to match Python).
            var ema200_5 = EMA.Compute(closes5, emaLongPeriod);
            var ema20_5  = EMA.Compute(closes5, emaShortPeriod);
            // Session VWAP: for first-cut we treat the rolling window as one session.
            // Production wants a real session-start index from SessionCalendar.
            var vwap_5   = SessionVWAP.Compute(closes5, volumes5, new[] { 0 });
            var atr_5    = WilderATR.Compute(highs5, lows5, closes5, atrPeriod);

            double? atrLast = atr_5[atr_5.Count - 1];
            if (!atrLast.HasValue || atrLast.Value <= 0) return;

            // Build 60m TrendFilter.
            int n60 = Math.Min(CurrentBars[1] + 1, 250);
            var closes60 = new List<double>(n60);
            for (int btsIdx = n60 - 1; btsIdx >= 0; btsIdx--)
                closes60.Add(Closes[1][btsIdx] / TickSize_Indices);
            var ema60_50  = EMA.Compute(closes60, emaTrendShort);
            var ema60_200 = EMA.Compute(closes60, emaTrendLong);
            double? e50  = ema60_50 [ema60_50.Count  - 1];
            double? e200 = ema60_200[ema60_200.Count - 1];
            if (!e50.HasValue || !e200.HasValue) return;
            var trend60 = new TrendFilter60m(e50.Value, e200.Value, closes60[closes60.Count - 1]);

            // No-trade gates we can evaluate locally.
            var ntCtx = new NoTradeContext
            {
                EtTime = barTimeEt.TimeOfDay,
                BboPresent = true,
                OsmState = "FLAT"
            };
            var blockers = NoTrade.BlockingReasons(ntCtx);
            if (blockers.Count > 0) return;

            // Entry rules.
            EntrySignal sig = Rules.LongSignal(bars5m, ema200_5, ema20_5, vwap_5, trend60);
            if (sig == null) sig = Rules.ShortSignal(bars5m, ema200_5, ema20_5, vwap_5, trend60);
            if (sig == null) return;

            // Stop/target plan. We use the current Close as a proxy for the next
            // ask/bid pre-fill — fine for OnBarClose entries.
            int currentPx = ToTicks(Closes[0][0]);
            StopTargetPlan plan = sig.Side == EntrySide.Long
                ? Rules.PlanLong(sig.PullbackLowOrHigh, currentPx, slippageTicks, atrLast.Value)
                : Rules.PlanShort(sig.PullbackLowOrHigh, currentPx, slippageTicks, atrLast.Value);

            if (plan.SkipReason != null) return;

            // Convert ticks back to NT8 index-point units for stop/target.
            double stopPx   = plan.CandidateStop * TickSize_Indices;
            // Use a placeholder target = entry +/- 1.5*candidateR until the actual
            // fill price is known, then refine in OnExecutionUpdate. For OnBarClose
            // sim use the candidate plan's R directly.
            double r        = plan.CandidateR * TickSize_Indices;
            double targetPx = sig.Side == EntrySide.Long
                ? Closes[0][0] + 1.5 * r
                : Closes[0][0] - 1.5 * r;

            string sigName = sig.Side == EntrySide.Long ? "LongV02" : "ShortV02";
            SetStopLoss(sigName, CalculationMode.Price, stopPx, false);
            SetProfitTarget(sigName, CalculationMode.Price, targetPx);

            if (sig.Side == EntrySide.Long)
                EnterLong(contractsPerEntry, sigName);
            else
                EnterShort(contractsPerEntry, sigName);

            sessionCounters.OnEntry();
        }

        protected override void OnPositionUpdate(Position position, double averagePrice,
                                                 int quantity, MarketPosition marketPosition)
        {
            // When we go flat after being in a trade, decrement open positions counter.
            if (marketPosition == MarketPosition.Flat)
                sessionCounters?.OnExit();
        }

        private static int ToTicks(double price) => (int)Math.Round(price / TickSize_Indices);

        private static DateTime ToEasternTime(DateTime t)
        {
            // NT bar Time is in the chart's display timezone. For Sim101 most
            // users default to ET. Treat as ET unless the user has changed it.
            // Production should convert from t.Kind == Utc explicitly.
            return t;
        }
    }
}
