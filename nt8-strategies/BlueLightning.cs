/* BlueLightning Automated Trading System
Author Jacob Amaral Youtube Channel : Jacob Amaral
Note : This code works with the NinjaTrader platform, if your using something else you will have to convert the code if you want it to work with TradeStation,MetaTrader,Multicharts,Python etc....
NQ 10 minute bars
Trading Hours 9:30am-4pm EST / US Equities RTH (Real-time hours)
Optimization Instructions :
profitTarget : 1000,1500 increment 1250
stopLoss : 750, 1250 increment 1250
Optimization period 365
Test Period 365 days
Optimize On Max profit factor
*/
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
	public class BlueLightning : Strategy
	{
		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Enter the description for your new custom Strategy here.";
				Name										= "BlueLightning";
				Calculate									= Calculate.OnBarClose;
				EntriesPerDirection							= 1;
				EntryHandling								= EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy				= true;
				ExitOnSessionCloseSeconds					= 30;
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
				TP = 1250;
				SL = 750;
			}
			else if (State == State.Configure)
			{
				SetProfitTarget(CalculationMode.Price, TP);
				SetStopLoss(CalculationMode.Currency, SL);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar < 20) return;
			//If the current close price crosses below the 200 ema and the SMA is rising and intra price is starting to curl down enter short.
			if (Close[0] >= EMA(Close,200)[0] && Close[1] < EMA(Close,200)[1] && SMA(Close,20)[0] > SMA(Close,20)[1] && MACD(12,26,9).Diff[0] <= 0) {
				SetProfitTarget(CalculationMode.Price, Close[0]-ATR(20)[0]*TP); //set a $ profit target multiplied by the current Average True Range.
				EnterShort();
			}
			if (Low[0] > Bollinger(2,20).Upper[0] && Momentum(Close,5)[0] > Momentum(Close,5)[4]) {
				SetProfitTarget(CalculationMode.Price, Close[0]+ATR(20)[0]*TP); //set a $ profit target multiplied by the current Average True Range.
				EnterLong();
			}
		}
		
		#region Properties
		[NinjaScriptProperty]
		[Display(ResourceType = typeof(Custom.Resource), Name = "Profit Target", Order = 0)]
	    public double TP
	    { get; set; }
		[NinjaScriptProperty]
		[Display(ResourceType = typeof(Custom.Resource), Name = "Stop Loss", Order = 0)]
	    public double SL
	    { get; set; }
		#endregion
	}
}
