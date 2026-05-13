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
	public class Tom3 : Strategy
	{
		private EMA EMA200;
		private EMA EMA5;
		private bool key1 =false;
		private bool key2 =false;
		private double EMArange;
		private bool Short = false;
		private bool Long = false;
		private RSI RSI1;
		private int BarsSinceKey1=0;
		SessionIterator sessionIterator;


		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Enter the description for your new custom Strategy here.";
				Name										= "Tom3";
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
				EMArange1 = 40;
				EMArange1 = 70;
			}
			else if (State == State.Configure)
			{
				//SetStopLoss(CalculationMode.Currency, 2222);
				//SetProfitTarget(CalculationMode.Currency, 6666);	
			}
			else if (State == State.DataLoaded)
			{		
				EMA200 = EMA(Closes[0],200); // 20 day moving average	
				EMA5 = EMA(Closes[0],20);
				AddChartIndicator(EMA200);
			    AddChartIndicator(EMA5);
				RSI1 = RSI(Closes[0],14,3);				
			}
			 else if (State == State.Historical)
		   {
				sessionIterator = new SessionIterator(Bars);		
		   }
			
		}

		protected override void OnBarUpdate()
		{
			if (Bars.IsFirstBarOfSession)
			{
			    sessionIterator.GetNextSession(Time[0], true);	
			}	
			
			if (Time[0] >= sessionIterator.ActualSessionEnd.AddSeconds(-180) && Time[0] <= sessionIterator.ActualSessionEnd && BarsInProgress != 1)
			{
				ExitShort(0,1,"ExitOnClose","");
				ExitLong(0,1,"ExitOnClose","");
				return;
			}	
			
			if (CurrentBars[0] < 200)
			    return;
			
			
		 	if (Bars.IsFirstBarOfSession)
			{
			    key1 = false;
			    key2 = false;
			    Short = false;
				Long = false;
			  }
			
			
			EMArange=Math.Abs(EMA200[0]-EMA5[0]);
			
			if (Position.MarketPosition != MarketPosition.Flat) return;
			
			if (EMArange > EMArange1)
			{
				key1=true;
				if (Close[0]<EMA200[0])
					Short=true;		
				if (Close[0]>EMA200[0])
					Long=true;	
			}
			
					
			if (EMArange>EMArange2)
			{
				if (Short && Long==true)
				{
					EnterShort();
					Short=false;

				}
				else
				{
					EnterLong();
					Long=false;
				}
				key1=key2=false;
			}
			
		}
		
		#region Properties
		
		[NinjaScriptProperty]
        [Display(Name = "EMArange1", GroupName = "Parameters", Order = 1)]
        public int EMArange1 { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "EMArange2", GroupName = "Parameters", Order = 2)]
        public int EMArange2
		{ get; set;} 
		
		#endregion		
	}
}
