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
	public class VariableTrend : Strategy
	{
		private VMA vma;
		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Variable Moving Average is an exponential moving average that automatically adjusts its smoothing percentage based on market volatility. Giving more weight to the current data increases sensitivity thus making it a better signal indicator for short and long term markets.";
				Name										= "VariableTrend";
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
				stopLoss = 1000;
			}
			else if (State == State.Configure)
			{
				SetStopLoss(CalculationMode.Currency, stopLoss);
				vma = VMA(9, 9);
				AddChartIndicator(vma);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CrossAbove(Close,vma,1)) EnterLong();
			if (CrossBelow(Close,vma,1)) EnterShort();
		}
		
		[NinjaScriptProperty]
		[Display(ResourceType = typeof(Custom.Resource), Name = "Stop Loss In $", Order = 0)]
	    public double stopLoss
	    { get; set; }
	}
}
