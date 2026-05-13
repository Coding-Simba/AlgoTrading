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
    public class Tom3LossGuard : Strategy
    {
        private EMA EMA200;
        private EMA EMA20;
        private bool key1 = false;
        private bool key2 = false;
        private double EMArange;
        private bool Short = false;
        private bool Long = false;
        private RSI RSI1;
        private SessionIterator sessionIterator;

        // Loss-guard state
        private bool blockedThisSession = false;
        private bool lossGuardExitedThisSession = false;
        private double maxUnrealizedPnl = 0;
        private int entryBarNumber = -1;
        private MarketPosition lastMarketPosition = MarketPosition.Flat;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Tom3 with targeted loss guards. Original Tom3 entry structure and original bugged direction logic are preserved.";
                Name = "Tom3 LossGuard";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 20;
                IsInstantiatedOnEachOptimizationIteration = true;

                // Real Tom3 thresholds from your Strategy Analyzer settings.
                EMArange1 = 40;
                EMArange2 = 70;

                // First test: only block the specific suspicious condition.
                UsePureShortLongBlock = true;
                BlockedSetupSkipsWholeSession = false;

                // Optional guards disabled by default. Test one at a time.
                UseCurrentDirectionLongValidation = false;
                RequireEMA20AboveEMA200ForLong = false;
                UseNeverWorkedEmergencyExit = false;
                NeverWorkedMinutes = 360;
                NeverWorkedMaxMFECurrency = 1000;
                NeverWorkedLossTriggerCurrency = 5000;
                PreventReentryAfterLossGuardExit = true;

                EnableDebugPrint = false;
            }
            else if (State == State.Configure)
            {
                // No stop, no target, no trailing stop. Tom3's original exit behavior is preserved.
            }
            else if (State == State.DataLoaded)
            {
                EMA200 = EMA(Closes[0], 200);
                EMA20 = EMA(Closes[0], 20);
                AddChartIndicator(EMA200);
                AddChartIndicator(EMA20);
                RSI1 = RSI(Closes[0], 14, 3);
            }
            else if (State == State.Historical)
            {
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

                key1 = false;
                key2 = false;
                Short = false;
                Long = false;
                blockedThisSession = false;
                lossGuardExitedThisSession = false;
                maxUnrealizedPnl = 0;
                entryBarNumber = -1;
            }

            // Original Tom3 manual end-of-session exit: exit during the last 3 minutes of the active session.
            if (Time[0] >= sessionIterator.ActualSessionEnd.AddSeconds(-180) && Time[0] <= sessionIterator.ActualSessionEnd)
            {
                ExitShort(0, 1, "ExitOnClose", "");
                ExitLong(0, 1, "ExitOnClose", "");
                lastMarketPosition = Position.MarketPosition;
                return;
            }

            if (CurrentBars[0] < 200)
            {
                lastMarketPosition = Position.MarketPosition;
                return;
            }

            // Track MFE for the optional "never worked" exit.
            UpdateOpenTradeTracking();

            // Optional narrow emergency exit. This is not the old broad TimeFailure rule.
            // It only exits if the trade has been open for a long time, has barely worked, and is now deeply negative.
            if (UseNeverWorkedEmergencyExit && Position.MarketPosition != MarketPosition.Flat)
            {
                double currentPnl = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
                int barsInTrade = entryBarNumber >= 0 ? CurrentBar - entryBarNumber : 0;

                if (barsInTrade >= NeverWorkedMinutes
                    && maxUnrealizedPnl < NeverWorkedMaxMFECurrency
                    && currentPnl <= -Math.Abs(NeverWorkedLossTriggerCurrency))
                {
                    if (Position.MarketPosition == MarketPosition.Long)
                        ExitLong(0, 1, "NeverWorkedExit", "");
                    else if (Position.MarketPosition == MarketPosition.Short)
                        ExitShort(0, 1, "NeverWorkedExit", "");

                    lossGuardExitedThisSession = true;

                    if (EnableDebugPrint)
                        Print(string.Format("{0} NeverWorkedExit. PnL={1:F2}, MaxMFE={2:F2}, BarsInTrade={3}", Time[0], currentPnl, maxUnrealizedPnl, barsInTrade));

                    lastMarketPosition = Position.MarketPosition;
                    return;
                }
            }

            EMArange = Math.Abs(EMA200[0] - EMA20[0]);

            // Original Tom3: do not look for new entries while already in a position.
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                lastMarketPosition = Position.MarketPosition;
                return;
            }

            if (PreventReentryAfterLossGuardExit && lossGuardExitedThisSession)
            {
                lastMarketPosition = Position.MarketPosition;
                return;
            }

            if (BlockedSetupSkipsWholeSession && blockedThisSession)
            {
                lastMarketPosition = Position.MarketPosition;
                return;
            }

            // Original Tom3 stage 1: when EMA spread exceeds EMArange1, set direction flags.
            if (EMArange > EMArange1)
            {
                key1 = true;

                if (Close[0] < EMA200[0])
                    Short = true;

                if (Close[0] > EMA200[0])
                    Long = true;
            }

            // Original Tom3 stage 2: when EMA spread exceeds EMArange2, enter using the original bugged logic.
            if (EMArange > EMArange2)
            {
                bool pureShortOnly = Short == true && Long == false;

                // Preserve original bug exactly: only shorts when BOTH flags are true; otherwise long.
                bool bugWouldShort = Short && Long == true;
                bool bugWouldLong = !bugWouldShort;

                // Targeted Guard 1: if the only flag is bearish, but the bug would force a long, skip the entry.
                if (UsePureShortLongBlock && pureShortOnly && bugWouldLong)
                {
                    blockedThisSession = true;

                    if (EnableDebugPrint)
                        Print(string.Format("{0} PureShortLongBlock skipped forced LONG. EMArange={1:F2}, Close={2:F2}, EMA200={3:F2}, Short={4}, Long={5}", Time[0], EMArange, Close[0], EMA200[0], Short, Long));

                    // Important: do not reset Short/Long here by default.
                    // This lets the original state machine continue. If price later sets Long=true,
                    // the original Tom3 bug may still allow a short.
                    return;
                }

                // Targeted Guard 2: optional current long validation at the actual entry bar.
                if (UseCurrentDirectionLongValidation && bugWouldLong)
                {
                    bool invalidLong = Close[0] < EMA200[0];

                    if (RequireEMA20AboveEMA200ForLong)
                        invalidLong = invalidLong || EMA20[0] < EMA200[0];

                    if (invalidLong)
                    {
                        blockedThisSession = true;

                        if (EnableDebugPrint)
                            Print(string.Format("{0} CurrentDirectionLongValidation skipped LONG. EMArange={1:F2}, Close={2:F2}, EMA20={3:F2}, EMA200={4:F2}, Short={5}, Long={6}", Time[0], EMArange, Close[0], EMA20[0], EMA200[0], Short, Long));

                        return;
                    }
                }

                // Original Tom3 bugged direction logic preserved.
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

                key1 = key2 = false;
            }

            lastMarketPosition = Position.MarketPosition;
        }

        private void UpdateOpenTradeTracking()
        {
            // Detect a new open trade after a historical/realtime fill.
            if (lastMarketPosition == MarketPosition.Flat && Position.MarketPosition != MarketPosition.Flat)
            {
                entryBarNumber = CurrentBar;
                maxUnrealizedPnl = 0;
            }

            if (Position.MarketPosition != MarketPosition.Flat)
            {
                double currentPnl = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);
                if (currentPnl > maxUnrealizedPnl)
                    maxUnrealizedPnl = currentPnl;
            }

            if (Position.MarketPosition == MarketPosition.Flat && lastMarketPosition != MarketPosition.Flat)
            {
                entryBarNumber = -1;
                maxUnrealizedPnl = 0;
            }
        }

        #region Properties

        [NinjaScriptProperty]
        [Display(Name = "EMArange1", GroupName = "01. Original Tom3 Parameters", Order = 1)]
        public int EMArange1 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "EMArange2", GroupName = "01. Original Tom3 Parameters", Order = 2)]
        public int EMArange2 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "UsePureShortLongBlock", Description = "If Short=true and Long=false, but Tom3's bug would force a long, skip the entry.", GroupName = "02. Loss Cause Guards", Order = 10)]
        public bool UsePureShortLongBlock { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "BlockedSetupSkipsWholeSession", Description = "If true, one blocked setup prevents new entries until next session. If false, the original flag machine can continue.", GroupName = "02. Loss Cause Guards", Order = 11)]
        public bool BlockedSetupSkipsWholeSession { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "UseCurrentDirectionLongValidation", Description = "Optional: block bug-forced longs when the current bar is below EMA200.", GroupName = "02. Loss Cause Guards", Order = 20)]
        public bool UseCurrentDirectionLongValidation { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "RequireEMA20AboveEMA200ForLong", Description = "Optional stricter long validation. If enabled, long is also blocked when EMA20 is below EMA200.", GroupName = "02. Loss Cause Guards", Order = 21)]
        public bool RequireEMA20AboveEMA200ForLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "UseNeverWorkedEmergencyExit", Description = "Optional narrow exit for trades that have barely worked and are deeply negative after many minutes.", GroupName = "03. Narrow Emergency Exit", Order = 30)]
        public bool UseNeverWorkedEmergencyExit { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "NeverWorkedMinutes", Description = "Because this strategy runs on 1-minute bars, minutes equal bars.", GroupName = "03. Narrow Emergency Exit", Order = 31)]
        public int NeverWorkedMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(0, double.MaxValue)]
        [Display(Name = "NeverWorkedMaxMFECurrency", GroupName = "03. Narrow Emergency Exit", Order = 32)]
        public double NeverWorkedMaxMFECurrency { get; set; }

        [NinjaScriptProperty]
        [Range(0, double.MaxValue)]
        [Display(Name = "NeverWorkedLossTriggerCurrency", GroupName = "03. Narrow Emergency Exit", Order = 33)]
        public double NeverWorkedLossTriggerCurrency { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "PreventReentryAfterLossGuardExit", GroupName = "03. Narrow Emergency Exit", Order = 34)]
        public bool PreventReentryAfterLossGuardExit { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "EnableDebugPrint", GroupName = "99. Debug", Order = 99)]
        public bool EnableDebugPrint { get; set; }

        #endregion
    }
}
