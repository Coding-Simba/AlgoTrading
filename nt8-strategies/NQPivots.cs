/* NQPivots Strategy
 * NQ 1 minute Bars
 * US Equities RTH (9:30am - 4pm EST) Trading Hours
 * Exit on session close checked
 */
#region Using declarations
using System;
using Microsoft.CSharp;
using System.IO;
using System.Collections.Generic;
using System.Collections;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
using System.Windows.Media;
using System.Globalization;
using System.Text;
#endregion
namespace NinjaTrader.NinjaScript.Strategies
{
    public class TimeAtr
    {
        public DateTime Date { get; set; }
        public double ATR { get; set; }

        public TimeAtr(DateTime date, double atr)
        {
            Date = date;
            ATR = atr;
        }
    }
    public class NQPivots : Strategy
    {
        private EMA doubleTopBottomEMAFast;
        private EMA doubleTopBottomEMASlow;
        private bool lastLong = false;
        private bool lastShort = false;
        private bool breakevenTriggered = false;
        protected override void OnStateChange()
        {
            //OnSetDefaults, think of this as a constructor, ran first when a strategy is enabled set Ninja and class default variables
            if (State == State.SetDefaults)
            {
                Name = "NQPivots";
                Calculate = Calculate.OnBarClose; DaysToLoad = 2000;
                EntriesPerDirection = 1;
                StartBehavior = StartBehavior.ImmediatelySubmitSynchronizeAccount;
                EntryHandling = EntryHandling.AllEntries;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 2;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.IgnoreAllErrors;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 1;
                IncludeTradeHistoryInBacktest = true; IncludeCommission = true;
                IsExitOnSessionCloseStrategy = true;
                IncludeTradeHistoryInBacktest = true;
                // See the Help Guide for additional information
                IsInstantiatedOnEachOptimizationIteration = false;
                sellProfit = 0;
                sellBars = 0;
                profitTarget = 200;
                stopLoss = 400;
                trailStop = 0;
                useATR = false;
                useCurrency = false;
                usePerc = false;
                breakevenProfit = 0;
                reverseTrade = false;
            }
            //OnStateConfigure, read variables from properties in front-end to start strategy run
            else if (State == State.Configure)
            {
                //For Pattern Detect
                doubleTopBottomEMAFast = EMA(7);
                doubleTopBottomEMASlow = EMA(14);

                doubleTopBottomEMAFast.Plots[0].Brush = Brushes.Goldenrod;
                doubleTopBottomEMASlow.Plots[0].Brush = Brushes.SeaGreen;
                //Reset targets!
                //Profit Targets, Trail Stops, Stop Losses
                #region Targets
                // Exit at Profit Type in Percent
                if (!useATR && (profitTarget > 0 || stopLoss > 0))
                {
                    //If the execution bars in progress is the same as the original bars we are not trading in a list
                    try
                    {
                        if (usePerc)
                        {
                            // Exit profit target ticks
                            if (profitTarget > 0)
                            {
                                SetProfitTarget(CalculationMode.Percent, profitTarget / 100.00d);
                            }

                            // Exit stop loss ticks
                            if (stopLoss > 0)
                            {
                                SetStopLoss(CalculationMode.Percent, stopLoss / 100.00d);
                            }
                        }
                        else if (useCurrency)
                        {
                            // Exit profit target currency
                            if (profitTarget > 0)
                            {
                                SetProfitTarget(CalculationMode.Currency, profitTarget * DefaultQuantity);
                            }

                            // Exit stop loss ticks
                            if (stopLoss > 0)
                            {
                                SetStopLoss(CalculationMode.Currency, stopLoss * DefaultQuantity);
                            }
                        }
                        else
                        {
                            // Exit profit target ticks
                            if (profitTarget > 0)
                            {
                                SetProfitTarget(CalculationMode.Ticks, profitTarget);
                            }

                            // Exit stop loss ticks
                            if (stopLoss > 0)
                            {
                                SetStopLoss(CalculationMode.Ticks, stopLoss);
                            }
                        }
                    }
                    catch (Exception e) { Print(e.Message); }
                }
                // Exit at Trail Stop
                //Trailing Stop is a bit more complicated, right now only works with 100% exit size
                if (trailStop > 0 && !useATR)
                {
                    if (usePerc)
                    {
                        //Set Trailing Stops percent once 
                        SetTrailStop(CalculationMode.Percent, trailStop / 100.00d);
                    }
                    else
                    {
                        //							Set Trailing Stops ticks once 
                        SetTrailStop(CalculationMode.Ticks, trailStop);
                    }
                }
            }
            #endregion
        }

        //<summary>
        //OnBarUpdate, anytime we get data run strategy logic
        //</summary>
        protected override void OnBarUpdate()
        {
            if (CurrentBar < 20) return; if (TradingHours == TradingHours.Get("US Equities RTH") && Time[0].Hour >= 16) return;
            if (Bars.IsFirstBarOfSession)
            {
                lastLong = false;
                lastShort = false;
            }
            #region Entry Signals
            if (Close[0] > CamarillaPivots(PivotRange.Daily, HLCCalculationMode.CalcFromIntradayData, 0, 0, 0, 20).S1[0] && Close[1] < CamarillaPivots(PivotRange.Daily, HLCCalculationMode.CalcFromIntradayData, 0, 0, 0, 20).S1[0])
            {
                //ATR
                if (useATR)
                {
                    // Exit profit target atr
                    if (profitTarget > 0)
                    {
                        SetProfitTarget(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize) * profitTarget * ATR(20)[0]);
                    }

                    // Exit stop loss atr
                    if (stopLoss > 0)
                    {
                        SetStopLoss(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize) * stopLoss * ATR(20)[0]);
                    }
                    // Trail Stop atr
                    if (trailStop > 0)
                    {
                        SetTrailStop(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize) * trailStop * ATR(20)[0]);
                    }
                }
                EnterLong(); lastLong = true; lastShort = false;

            }
            if (Close[0] < CamarillaPivots(PivotRange.Daily, HLCCalculationMode.CalcFromIntradayData, 0, 0, 0, 20).R3[0] && Close[1] > CamarillaPivots(PivotRange.Daily, HLCCalculationMode.CalcFromIntradayData, 0, 0, 0, 20).R3[0])
            {
                //ATR
                if (useATR)
                {
                    // Exit profit target atr
                    if (profitTarget > 0)
                    {
                        SetProfitTarget(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize) * profitTarget * ATR(20)[0]);
                    }

                    // Exit stop loss atr
                    if (stopLoss > 0)
                    {
                        SetStopLoss(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize) * stopLoss * ATR(20)[0]);
                    }
                    // Trail Stop atr
                    if (trailStop > 0)
                    {
                        SetTrailStop(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize) * trailStop * ATR(20)[0]);
                    }
                }
                EnterShort(); lastLong = false; lastShort = true;

            }
            #endregion
            #region Exit Signals
            //Exit after n bars in profit
            if (sellProfit > 0)
            {
                if (Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]) > 0 && BarsSinceEntryExecution() >= sellProfit - 1)
                {
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong();
                    if (Position.MarketPosition == MarketPosition.Short) ExitShort();
                }
            }
            //Exit after n bars
            if (sellBars > 0)
            {
                if (BarsSinceEntryExecution() >= sellBars - 1)
                {
                    if (Position.MarketPosition == MarketPosition.Long) ExitLong();
                    if (Position.MarketPosition == MarketPosition.Short) ExitShort();
                }
            }
            //Reverse Trade On Exit
            if (reverseTrade)
            {
                if ((BarsSinceExitExecution(0, "Profit target", 0) == 0 || BarsSinceExitExecution(0, "Stop loss", 0) == 0 || BarsSinceExitExecution(0, "Trail stop", 0) == 0) && lastLong)
                {
                    EnterShort();
                    lastShort = true;
                    lastLong = false;
                }
                else if ((BarsSinceExitExecution(0, "Profit target", 0) == 0 || BarsSinceExitExecution(0, "Stop loss", 0) == 0 || BarsSinceExitExecution(0, "Trail stop", 0) == 0) && lastShort)
                {
                    EnterLong();
                    lastLong = true;
                    lastShort = false;
                }
            }
            if (breakevenProfit > 0)
            {
                #region Reset stops
                if (Position.MarketPosition == MarketPosition.Flat)
                {
                    if (useCurrency)
                    {
                        if (stopLoss != 0)
                        {
                            SetStopLoss("Sell short", CalculationMode.Currency, stopLoss * DefaultQuantity, true);
                            SetStopLoss("Buy", CalculationMode.Currency, stopLoss * DefaultQuantity, true);
                        }
                        if (profitTarget != 0)
                        {
                            SetProfitTarget("Buy", CalculationMode.Currency, profitTarget * DefaultQuantity, true);
                            SetProfitTarget("Sell short", CalculationMode.Currency, profitTarget * DefaultQuantity, true);
                        }
                    }
                    else if (!useATR)
                    {
                        if (stopLoss != 0)
                        {
                            SetStopLoss("Sell short", CalculationMode.Ticks, stopLoss, true);
                            SetStopLoss("Buy", CalculationMode.Ticks, stopLoss, true);
                        }
                        if (profitTarget != 0)
                        {
                            SetProfitTarget("Buy", CalculationMode.Ticks, profitTarget, true);
                            SetProfitTarget("Sell short", CalculationMode.Ticks, profitTarget, true);
                        }
                    }
                    breakevenTriggered = false;
                }
                #endregion

                #region Breakeven Code
                if (Position.MarketPosition != MarketPosition.Flat && (Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]) >= breakevenProfit) && !breakevenTriggered)
                {
                    SetStopLoss("Sell short", CalculationMode.Price, Position.AveragePrice, true);
                    SetStopLoss("Buy", CalculationMode.Price, Position.AveragePrice, true);
                    breakevenTriggered = true;
                }
                #endregion
            }
            #endregion
        }
        [Range(0, int.MaxValue), NinjaScriptProperty]
        [Display(ResourceType = typeof(Custom.Resource), Name = "Profit Target", GroupName = "Exits", Order = 8)]
        public double profitTarget
        { get; set; }
        [Range(0, int.MaxValue), NinjaScriptProperty]
        [Display(ResourceType = typeof(Custom.Resource), Name = "Stop Loss", GroupName = "Exits", Order = 9)]
        public double stopLoss
        { get; set; }
        [Range(0, int.MaxValue), NinjaScriptProperty]
        [Display(ResourceType = typeof(Custom.Resource), Name = "Trail Stop", GroupName = "Exits", Order = 10)]
        public double trailStop
        { get; set; }
        [NinjaScriptProperty]
        [Display(ResourceType = typeof(Custom.Resource), Name = "Exit after n bars in profit", GroupName = "Exits", Order = 14)]
        public int sellProfit
        { get; set; }
        [NinjaScriptProperty]
        [Display(ResourceType = typeof(Custom.Resource), Name = "Exit after n bars", GroupName = "Exits", Order = 14)]
        public int sellBars
        { get; set; }
        [Display(ResourceType = typeof(Custom.Resource), Name = "Use ATR", GroupName = "Exits", Order = 15)]
        public bool useATR
        { get; set; }
        [Display(ResourceType = typeof(Custom.Resource), Name = "Use Currency", GroupName = "Exits", Order = 15)]
        public bool useCurrency
        { get; set; }
        [Display(ResourceType = typeof(Custom.Resource), Name = "Reverse Trade", GroupName = "Exits", Order = 15)]
        public bool reverseTrade
        { get; set; }
        [Display(ResourceType = typeof(Custom.Resource), Name = "Use Percent Calc", GroupName = "Exits", Order = 15)]
        public bool usePerc
        { get; set; }
        [NinjaScriptProperty]
        [Display(ResourceType = typeof(Custom.Resource), Name = "Breakeven Wait Profit", GroupName = "Exits", Order = 15)]
        public double breakevenProfit
        { get; set; }
    }
}
