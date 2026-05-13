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

//This namespace holds Strategies in this folder and is required. Do not change it. 
namespace NinjaTrader.NinjaScript.Strategies
{
	
	public class Achour002 : Strategy
	{
		private ATRTrailing ATRTrailing1;
		private ATRTrailing ATRTrailing2;
		
		private EMA EMA10;
		private RSI RSI1;
		//private EMA EMA;
		//private Stochastics Stochastics1;
		private int Barssinenentry1;
		private ATR ATR1;
		SessionIterator sessionIterator;
		
		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Enter the description for your new custom Strategy here.";
				Name										= "Achour002";
				Calculate									= Calculate.OnBarClose;
				EntriesPerDirection							= 1;
				EntryHandling								= EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy				= true;
				ExitOnSessionCloseSeconds					= 120;
				IsFillLimitOnTouch							= false;
				MaximumBarsLookBack							= MaximumBarsLookBack.TwoHundredFiftySix;
				OrderFillResolution							= OrderFillResolution.Standard;
				Slippage									= 0;
				StartBehavior								= StartBehavior.WaitUntilFlat;
				TimeInForce									= TimeInForce.Gtc;
				TraceOrders									= false;
				RealtimeErrorHandling						= RealtimeErrorHandling.StopCancelClose;
				StopTargetHandling							= StopTargetHandling.PerEntryExecution;
				BarsRequiredToTrade							= 20;
				// Disable this property for performance gains in Strategy Analyzer optimizations
				// See the Help Guide for additional information
				IsInstantiatedOnEachOptimizationIteration	= true;
				RSI_High = 70;
				RSI_Low = 30;
			}
			else if (State == State.Configure)
			{
				//SetTrailStop(CalculationMode.Percent, 0.01);
				//SetStopLoss(CalculationMode.Currency, 999);
				//SetProfitTarget(CalculationMode.Currency, 5000);
				
				AddDataSeries(Data.BarsPeriodType.Minute, 20);
				//AddDataSeries(Data.BarsPeriodType.Day, 1);
			}
			else if (State == State.DataLoaded)
			{
				ATRTrailing1 = ATRTrailing(Closes[1], 4,10, 0.005);
				ATRTrailing2 = ATRTrailing(Close, 4,10, 0.005);				
				//EMA10 = EMA(Closes[1],200); // 20 day moving average	
				RSI1 = RSI(Closes[0],14,3);
				//EMA = EMA(Closes[1],50);
				//Stochastics1				= Stochastics(Closes[1], 7, 14, 3);
				ATR1=ATR(Close,10);	
			}
		   else if (State == State.Historical)
		   {
				sessionIterator = new SessionIterator(Bars);		
		   }			
			
		}

		protected override void OnBarUpdate()
		{
			if (Bars.IsFirstBarOfSession && BarsInProgress != 1)
			{
			    sessionIterator.GetNextSession(Time[0], true);	
			}	
			
			if (Time[0] >= sessionIterator.ActualSessionEnd.AddSeconds(-120) && Time[0] <= sessionIterator.ActualSessionEnd && BarsInProgress != 1)
			{
				ExitShort(0,1,"ExitOnClose","");
				ExitLong(0,1,"ExitOnClose","");
				return;
			}	
			
			if (CurrentBars[0] < BarsRequiredToTrade || CurrentBars[1] < BarsRequiredToTrade) return;// && CurrentBars[2] < BarsRequiredToTrade) return;
			
			if (ATRTrailing2.Upper[0]!=0 && ATRTrailing2.Lower[1]!=0 && Position.MarketPosition == MarketPosition.Flat &&  RSI1[0]>RSI_Low+15)//&& Close[0]>EMA10[0])
			{
				EnterLong();
			}
			if (ATRTrailing2.Upper[1]!=0 && ATRTrailing2.Lower[0]!=0 && Position.MarketPosition == MarketPosition.Flat && RSI1[0]<RSI_High-15)// &&Stochastics1.D[0] <= 80)// && Close[0]<EMA10[0])
			{
				EnterShort();
			}			
			if ((Close[0] < ATRTrailing1.Lower[0] && ATRTrailing1.Lower[0] !=0 || RSI1[0]<RSI_Low) && Barssinenentry1>2)//|| CrossBelow(EMA(Close,5),SMA(Closes[1],20),1)) //RSI did something nice
			{
				ExitLong();
			}
			if ((Close[0] > ATRTrailing1.Upper[0] && ATRTrailing1.Upper[0] !=0 || RSI1[0]>RSI_High) && Barssinenentry1>2)//|| CrossAbove(EMA(Close,5),SMA(Closes[1],20),1))
			{
				ExitShort();
			}	
			
			if (Low[0]<=Position.AveragePrice-ATR1[0]*10)
				ExitShort(0,1,"","");			
			
			if (Position.MarketPosition != MarketPosition.Flat && BarsInProgress == 1)
			{
				Barssinenentry1 ++;
			}
			else if (Position.MarketPosition == MarketPosition.Flat)
			{
				Barssinenentry1 =0;
			}
						
		}
		
		#region Properties
		
		[NinjaScriptProperty]
        [Display(Name = "RSI_High", GroupName = "Parameters", Order = 1)]
        public int RSI_High { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "RSI_Low", GroupName = "Parameters", Order = 2)]
        public int RSI_Low
		{ get; set;} 
		
		#endregion

				
	}
}
