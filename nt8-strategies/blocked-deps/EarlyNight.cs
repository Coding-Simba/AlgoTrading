
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
		#endregion
		namespace NinjaTrader.NinjaScript.Strategies
		{

			public class EarlyNight : Strategy
			{
				private NinjaTrader.Custom.Strategies.StratGenV2.DetectPatternsV2 detectPatterns = new NinjaTrader.Custom.Strategies.StratGenV2.DetectPatternsV2();
				private EMA doubleTopBottomEMAFast;
        		private EMA doubleTopBottomEMASlow;
				private bool lastLong = false;
				private bool lastShort = false;
			    protected override void OnStateChange()
	        {
            //OnSetDefaults, think of this as a constructor, ran first when a strategy is enabled set Ninja and class default variables
            if (State == State.SetDefaults)
            {
                Name = "EarlyNight";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                StartBehavior = StartBehavior.ImmediatelySubmitSynchronizeAccount;
                EntryHandling = EntryHandling.AllEntries;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 1;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.IgnoreAllErrors;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 1;
                IncludeCommission = true;
                IsExitOnSessionCloseStrategy = true;
                IncludeTradeHistoryInBacktest = true;
                // See the Help Guide for additional information
                IsInstantiatedOnEachOptimizationIteration = false;
                sellProfit = 0;
				profitTarget = 160;
				stopLoss = 120;
				trailStop = 0;
				useATR = false;
				usePerc = false;
				reverseTrade =  false;
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
							if (usePerc) {
								 // Exit profit target ticks
	                            if (profitTarget > 0)
	                            {
	                                SetProfitTarget(CalculationMode.Percent, profitTarget/100.00d);
	                            }
	
	                            // Exit stop loss ticks
	                            if (stopLoss > 0)
	                            {
	                                SetStopLoss(CalculationMode.Percent, stopLoss / 100.00d);
	                            }
							} else {
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
						if (usePerc) {
		                    //Set Trailing Stops percent once 
		                    SetTrailStop(CalculationMode.Percent, trailStop/100.00d);
						} else {
							//Set Trailing Stops ticks once 
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
				if (CurrentBar < 20) return;
				if (Bars.IsFirstBarOfSession)
            	{
                	lastLong = false;
                	lastShort = false;
            	}
				#region Entry Signals
				if (Open[0] > SMA(100)[0] && Open[1] < SMA(100)[0] && RSI(14, 3)[0] > 60) {
					//ATR
					if (useATR) {
						 // Exit profit target atr
	                    if (profitTarget > 0)
	                    {
	                        SetProfitTarget(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize)*profitTarget*ATR(20)[0]);
	                    }
	
	                    // Exit stop loss atr
	                    if (stopLoss > 0)
	                    {
	                        SetStopLoss(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize)*stopLoss*ATR(20)[0]);
	                    } 
						// Trail Stop atr
	                    if (trailStop > 0)
	                    {
	                    	SetTrailStop(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize)*trailStop*ATR(20)[0]);
	                    }
					}
					EnterLong();lastLong = true;lastShort = false;
					
				}
				if (Low[0] < SMA(100)[0] && Low[1] > SMA(100)[0] && Close[0] <= SMA(100)[0]) {
					//ATR
					if (useATR) {
						 // Exit profit target atr
	                    if (profitTarget > 0)
	                    {
	                        SetProfitTarget(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize)*profitTarget*ATR(20)[0]);
	                    }
	
	                    // Exit stop loss atr
	                    if (stopLoss > 0)
	                    {
	                        SetStopLoss(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize)*stopLoss*ATR(20)[0]);
	                    } 
						// Trail Stop atr
	                    if (trailStop > 0)
	                    {
	                    	SetTrailStop(CalculationMode.Ticks, (1 / Instrument.MasterInstrument.TickSize)*trailStop*ATR(20)[0]);
	                    }
					}
					EnterShort();lastLong = false;lastShort = true;
					
				}
				#endregion
	 			#region Exit Signals
	            //Exit after n bars	
	            if (sellProfit > 0)
	            {
	                if (Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]) > 0 && BarsSinceEntryExecution() >= sellProfit - 1)
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
	            #endregion
	        }

			private int checkPattern(string patternName) {
				try { // If Pattern draw it
				string signalToUse = patternName;
				string uniqId = Guid.NewGuid().ToString("N");
				if (patternName.Contains("Double"))
		        {
					// Pass in EMA Fast and Slow value for Double Top/Bottom
			        detectPatterns.setDTopBottomEMAFastAndSlowValue(doubleTopBottomEMAFast.Value[0], doubleTopBottomEMASlow.Value[0], 1);
			
			        // Find Double Top/Bottom with EMA
			        detectPatterns.findPatternWithEMA(Highs[BarsInProgress][0], Lows[BarsInProgress][0], Closes[BarsInProgress][0], Opens[BarsInProgress][0], 1, 1, patternName);
			
					if (detectPatterns.CheckIfPatternFound(1))
			        {
			            if (patternName == "DoubleTop")
			            {
			                int dTMidGap = detectPatterns.getDTMidGap(1);
			                double[] dTPricePoints = detectPatterns.getDTPricePoints(1);
			                double price = 0;
			
			                if (Opens[BarsInProgress][1] > Closes[BarsInProgress][1])
			                {
			                    price = Opens[BarsInProgress][1];
			                }
			                else
			                {
			                    price = Closes[BarsInProgress][1];
			                }
			
			                // Draw text and line to guide user
			                {
			                    Draw.Text(this, patternName + "-" + uniqId, patternName, dTMidGap, price + (price * 0.0003));
			                    Draw.Line(this, "doubletop-" + uniqId, true, 1, dTPricePoints[2], dTMidGap, dTPricePoints[2], Brushes.LimeGreen, DashStyleHelper.Solid, 2, true);
			                }
							return 1;
			            }
			            else if (patternName == "DoubleBottom")
			            {
			                int dBMidGap = detectPatterns.getDBMidGap(1);
			                double[] dBPricePoints = detectPatterns.getDBPricePoints(1);
			                double price = 0;
			
			                if (Opens[BarsInProgress][1] < Closes[BarsInProgress][1])
			                {
			                    price = Opens[BarsInProgress][1];
			                }
			                else
			                {
			                    price = Closes[BarsInProgress][1];
			                }
			                {
			                    // Draw text and line to guide user
			                    Draw.Text(this, patternName+ "-" + uniqId, patternName, dBMidGap, price * 0.9997);
			                    Draw.Line(this, "doublebottom-" + uniqId, true, 1, dBPricePoints[2], dBMidGap, dBPricePoints[2], Brushes.LimeGreen, DashStyleHelper.Solid, 2, true);
			                }
							return 1;
			            }
			        }
					return 0;
				}
            	return detectPatterns.checkPatternNew(Open,High,Low,Close,CurrentBar,Swing(5), this, patternName, Instrument.MasterInstrument.TickSize);
				} catch { return 0;}
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
	        [Display(ResourceType = typeof(Custom.Resource), Name = "Exit after n bars profit", GroupName = "Exits", Order = 14)]
	        public int sellProfit
	        { get; set; }
			[Display(ResourceType = typeof(Custom.Resource), Name = "Use ATR", GroupName = "Exits", Order = 15)]
	        public bool useATR
	        { get; set; }
			[Display(ResourceType = typeof(Custom.Resource), Name = "Reverse Trade", GroupName = "Exits", Order = 15)]
	        public bool reverseTrade
	        { get; set; }
			[Display(ResourceType = typeof(Custom.Resource), Name = "Use Percent Calc", GroupName = "Exits", Order = 15)]
	        public bool usePerc
	        { get; set; }
			}
		}
		
