#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

// This namespace holds Strategies in this folder and is required. Do not change it.
namespace NinjaTrader.NinjaScript.Strategies
{
    public class Tom3Trail : Strategy
    {
        private EMA EMA200;
        private EMA EMA5;
        private bool key1 = false;
        private bool key2 = false;
        private double EMArange;
        private bool Short = false;
        private bool Long = false;
        private RSI RSI1;
        private int BarsSinceKey1 = 0;
        private SessionIterator sessionIterator;

        // Protective wrapper state
        private bool tradeTakenThisSession = false;
        private bool positionTrackingInitialized = false;
        private bool delayedTrailActive = false;
        private bool protectiveExitSubmitted = false;
        private double bestUnrealizedCurrency = double.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = @"Tom3 with original bugged direction logic preserved, plus optional delayed trailing stop and catastrophe stop.";
                Name                                        = "Tom3 Trail";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 0;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 20;
                IsInstantiatedOnEachOptimizationIteration   = true;

                // Correct Tom3 settings from your analyzer screenshot.
                EMArange1 = 40;
                EMArange2 = 70;

                // Keep Tom3 one-trade-per-session personality after early protective exits.
                PreventReentrySameSession = true;

                // Main improvement candidate: delayed large-buffer trailing stop.
                UseDelayedTrailingStop = true;
                TrailingActivationCurrency = 5000;
                TrailingStopCurrency = 4000;

                // Tail-risk wrapper. Test 15000, 20000, 25000.
                UseCatastropheStop = true;
                CatastropheStopCurrency = 20000;

                // Optional fixed TP. Disabled by default because it may cap monster trend days.
                UseLargeTakeProfit = false;
                TakeProfitCurrency = 30000;

                EnableDebugPrint = false;
            }
            else if (State == State.Configure)
            {
                // Do not use SetStopLoss/SetProfitTarget here.
                // The wrappers are manual currency-based exits using current unrealized PnL.
                // This keeps the original Tom3 entry behavior intact and easy to compare.
            }
            else if (State == State.DataLoaded)
            {
                EMA200 = EMA(Closes[0], 200);
                EMA5 = EMA(Closes[0], 20);  // Original Tom3 called this EMA5, but it is actually EMA(20).
                AddChartIndicator(EMA200);
                AddChartIndicator(EMA5);
                RSI1 = RSI(Closes[0], 14, 3);
                sessionIterator = new SessionIterator(Bars);
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0)
                return;

            if (sessionIterator == null)
                sessionIterator = new SessionIterator(Bars);

            if (Bars.IsFirstBarOfSession)
            {
                sessionIterator.GetNextSession(Time[0], true);
                ResetSessionState();
            }

            if (CurrentBars[0] < 200)
                return;

            // Original Tom3 session-close behavior: flatten during final 3 minutes of the active session template.
            if (Time[0] >= sessionIterator.ActualSessionEnd.AddSeconds(-180)
                && Time[0] <= sessionIterator.ActualSessionEnd)
            {
                if (Position.MarketPosition != MarketPosition.Flat && !protectiveExitSubmitted)
                    SubmitProtectiveExit("ExitOnClose");

                return;
            }

            // Manage an open trade first. This is the only added risk logic.
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageOpenPosition();
                return;
            }
            else if (positionTrackingInitialized)
            {
                ResetTradeTrackingOnly();
            }

            if (PreventReentrySameSession && tradeTakenThisSession)
                return;

            EMArange = Math.Abs(EMA200[0] - EMA5[0]);

            // Original Tom3 stage-one flag logic preserved.
            if (EMArange > EMArange1)
            {
                key1 = true;

                if (Close[0] < EMA200[0])
                    Short = true;

                if (Close[0] > EMA200[0])
                    Long = true;
            }

            // Original Tom3 entry trigger preserved.
            if (EMArange > EMArange2)
            {
                // IMPORTANT: original Tom3 bugged direction logic intentionally preserved.
                // Do not change this to if (Short) / else if (Long) unless you want a different strategy.
                if (Short && Long == true)
                {
                    EnterShort();
                    Short = false;
                }
                else
                {
                    EnterLong();
                    Long = false;
                }

                tradeTakenThisSession = true;
                key1 = key2 = false;
            }
        }

        private void ManageOpenPosition()
        {
            if (!positionTrackingInitialized)
            {
                positionTrackingInitialized = true;
                delayedTrailActive = false;
                protectiveExitSubmitted = false;
                bestUnrealizedCurrency = double.MinValue;
            }

            double unrealizedCurrency = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);

            if (unrealizedCurrency > bestUnrealizedCurrency)
                bestUnrealizedCurrency = unrealizedCurrency;

            if (protectiveExitSubmitted)
                return;

            // Optional large fixed take-profit. Off by default.
            if (UseLargeTakeProfit && TakeProfitCurrency > 0 && unrealizedCurrency >= TakeProfitCurrency)
            {
                SubmitProtectiveExit("LargeTakeProfit");
                return;
            }

            // Catastrophe stop: not designed to improve every trade, only to cap disaster losses.
            if (UseCatastropheStop && CatastropheStopCurrency > 0 && unrealizedCurrency <= -CatastropheStopCurrency)
            {
                SubmitProtectiveExit("CatastropheStop");
                return;
            }

            // Delayed trailing stop:
            // 1. Let the trade breathe until it reaches the activation threshold.
            // 2. After activation, exit only if it gives back TrailingStopCurrency from peak open profit.
            if (UseDelayedTrailingStop && TrailingActivationCurrency > 0 && TrailingStopCurrency > 0)
            {
                if (!delayedTrailActive && bestUnrealizedCurrency >= TrailingActivationCurrency)
                {
                    delayedTrailActive = true;
                    DebugLog("Delayed trail activated. Best open PnL: " + bestUnrealizedCurrency.ToString("F2"));
                }

                if (delayedTrailActive && unrealizedCurrency <= bestUnrealizedCurrency - TrailingStopCurrency)
                {
                    SubmitProtectiveExit("DelayedTrailStop");
                    return;
                }
            }
        }

        private void SubmitProtectiveExit(string signalName)
        {
            protectiveExitSubmitted = true;
            DebugLog(signalName + " submitted. Position=" + Position.MarketPosition.ToString()
                + " Qty=" + Position.Quantity.ToString()
                + " Time=" + Time[0].ToString()
                + " BestOpenPnL=" + bestUnrealizedCurrency.ToString("F2"));

            if (Position.MarketPosition == MarketPosition.Long)
                ExitLong(0, Position.Quantity, signalName, "");
            else if (Position.MarketPosition == MarketPosition.Short)
                ExitShort(0, Position.Quantity, signalName, "");
        }

        private void ResetSessionState()
        {
            key1 = false;
            key2 = false;
            Short = false;
            Long = false;
            tradeTakenThisSession = false;
            ResetTradeTrackingOnly();
        }

        private void ResetTradeTrackingOnly()
        {
            positionTrackingInitialized = false;
            delayedTrailActive = false;
            protectiveExitSubmitted = false;
            bestUnrealizedCurrency = double.MinValue;
        }

        private void DebugLog(string message)
        {
            if (EnableDebugPrint)
                Print(Name + " | " + message);
        }

        #region Properties

        [NinjaScriptProperty]
        [Display(Name = "EMArange1", GroupName = "01. Original Tom3 Parameters", Order = 1)]
        public int EMArange1 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "EMArange2", GroupName = "01. Original Tom3 Parameters", Order = 2)]
        public int EMArange2 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "PreventReentrySameSession", GroupName = "02. Session Control", Order = 1)]
        public bool PreventReentrySameSession { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "UseDelayedTrailingStop", GroupName = "03. Delayed Trailing Stop", Order = 1)]
        public bool UseDelayedTrailingStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "TrailingActivationCurrency", GroupName = "03. Delayed Trailing Stop", Order = 2)]
        public double TrailingActivationCurrency { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "TrailingStopCurrency", GroupName = "03. Delayed Trailing Stop", Order = 3)]
        public double TrailingStopCurrency { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "UseCatastropheStop", GroupName = "04. Catastrophe Stop", Order = 1)]
        public bool UseCatastropheStop { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "CatastropheStopCurrency", GroupName = "04. Catastrophe Stop", Order = 2)]
        public double CatastropheStopCurrency { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "UseLargeTakeProfit", GroupName = "05. Optional Large Take Profit", Order = 1)]
        public bool UseLargeTakeProfit { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "TakeProfitCurrency", GroupName = "05. Optional Large Take Profit", Order = 2)]
        public double TakeProfitCurrency { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "EnableDebugPrint", GroupName = "99. Debug", Order = 1)]
        public bool EnableDebugPrint { get; set; }

        #endregion
    }
}
