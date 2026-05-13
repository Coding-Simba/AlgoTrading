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
	// Walid 1 — permission-filter version of Tom3.
	//
	// Goal: keep the original Tom3 entry behavior (including its preserved
	// direction-selection idiom) and only ADD optional entry-permission filters
	// that BLOCK bad entries before they happen. No active in-trade exits beyond
	// NinjaTrader's session-close flatten and an optional catastrophe stop.
	//
	// Removed vs. the previous defensive version:
	//   - TimeFailureExit            (was cutting winners after 240 min)
	//   - ProfitProtectionTrigger/Floor (was clipping winners)
	//   - NoLateEntryMinutes...      (was blocking valid late entries)
	//   - DailyLossLimit             (drawdown-management belongs elsewhere)
	//   - UseBearishLongBlock        (an entry-side hack on top of the bug)
	//
	// Kept:
	//   - End-of-session flatten 180s before session end (preserved Tom3).
	//   - Optional CatastropheStopCurrency: wide $-stop, off by default.
	//
	// Added:
	//   - PreventReentrySameSession
	//   - HTF trend filter
	//   - ATR regime filter
	//   - Opening-range confirmation (with optional retest)
	//   - SkipSundayGlobex
	public class Walid1 : Strategy
	{
		// Core Tom3 state.
		private EMA EMA200;
		private EMA EMA5;
		private bool key1 = false;
		private bool key2 = false;
		private double EMArange;
		private bool Short = false;
		private bool Long = false;
		private SessionIterator sessionIterator;

		// Re-entry guard.
		private bool enteredThisSession = false;
		private MarketPosition lastMarketPosition = MarketPosition.Flat;

		// HTF filter state.
		private EMA htfFast;
		private EMA htfSlow;

		// ATR regime state.
		private ATR atrShort;
		private SMA atrLongAvg;

		// Opening-range state.
		private double orHigh = double.MinValue;
		private double orLow = double.MaxValue;
		private bool orBreakoutLong = false;
		private bool orBreakoutShort = false;
		private bool orRetestLong = false;
		private bool orRetestShort = false;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Tom3 with optional entry-permission filters (HTF trend, ATR regime, opening range, Sunday Globex skip). Permission-only — no active in-trade exits beyond NT8 session-close and an optional wide catastrophe stop. Tom3 direction-selection idiom intentionally preserved.";
				Name										= "Walid 1";
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
				IsInstantiatedOnEachOptimizationIteration	= true;

				// 01. Core Tom3.
				EMArange1 = 40;
				EMArange2 = 70;
				PreventReentrySameSession = false;

				// 02. HTF trend filter.
				UseHigherTimeframeTrendFilter = false;
				HigherTimeframeMinutes = 60;
				HigherTrendFastEMA = 20;
				HigherTrendSlowEMA = 50;

				// 03. ATR regime filter.
				UseATRRegimeFilter = false;
				ATRPeriod = 14;
				ATRBaselinePeriod = 50;
				MinATRRatio = 0.80;
				MaxATRRatio = 1.80;

				// 04. Opening range filter.
				UseOpeningRangeConfirmation = false;
				OpeningRangeStartTime = 93000;
				OpeningRangeEndTime = 100000;
				RequireBreakoutRetest = false;

				// 05. Calendar filter.
				SkipSundayGlobex = false;

				// 06. Risk wrapper.
				UseCatastropheStopCurrency = false;
				CatastropheStopCurrency = 15000;

				// 99. Debug.
				EnableDebugPrint = false;
			}
			else if (State == State.Configure)
			{
				if (UseCatastropheStopCurrency && CatastropheStopCurrency > 0)
					SetStopLoss(CalculationMode.Currency, CatastropheStopCurrency);

				// HTF series is always added so it exists when the filter is toggled on.
				int htfMinutes = HigherTimeframeMinutes > 0 ? HigherTimeframeMinutes : 60;
				AddDataSeries(BarsPeriodType.Minute, htfMinutes);
			}
			else if (State == State.DataLoaded)
			{
				EMA200 = EMA(Closes[0], 200);
				EMA5 = EMA(Closes[0], 20);  // Original Tom3 named this EMA5 but it's EMA(20).
				AddChartIndicator(EMA200);
				AddChartIndicator(EMA5);

				htfFast = EMA(Closes[1], HigherTrendFastEMA > 0 ? HigherTrendFastEMA : 20);
				htfSlow = EMA(Closes[1], HigherTrendSlowEMA > 0 ? HigherTrendSlowEMA : 50);

				atrShort = ATR(Closes[0], ATRPeriod > 0 ? ATRPeriod : 14);
				atrLongAvg = SMA(atrShort, ATRBaselinePeriod > 0 ? ATRBaselinePeriod : 50);
			}
			else if (State == State.Historical)
			{
				sessionIterator = new SessionIterator(Bars);
			}
		}

		protected override void OnBarUpdate()
		{
			// Only act on primary 1-minute series.
			if (BarsInProgress != 0)
				return;

			if (CurrentBars[0] < 200)
				return;

			if (sessionIterator == null)
				sessionIterator = new SessionIterator(Bars);

			// 05. Calendar filter — Sunday Globex skip (early return).
			if (SkipSundayGlobex && Time[0].DayOfWeek == DayOfWeek.Sunday)
				return;

			if (Bars.IsFirstBarOfSession)
			{
				sessionIterator.GetNextSession(Time[0], true);
				key1 = false;
				key2 = false;
				Short = false;
				Long = false;

				// Per-session resets.
				enteredThisSession = false;

				orHigh = double.MinValue;
				orLow = double.MaxValue;
				orBreakoutLong = false;
				orBreakoutShort = false;
				orRetestLong = false;
				orRetestShort = false;
			}

			EMArange = Math.Abs(EMA200[0] - EMA5[0]);

			// Track re-entry state: once we've taken a trade and gone flat, no new entries this session.
			TrackReentryState();
			UpdateOpeningRangeState();

			// End-of-session flatten (preserved from Tom3).
			if (Time[0] >= sessionIterator.ActualSessionEnd.AddSeconds(-180)
				&& Time[0] <= sessionIterator.ActualSessionEnd)
			{
				if (Position.MarketPosition == MarketPosition.Long)
					ExitLong(0, Position.Quantity, "ExitOnClose", "");
				else if (Position.MarketPosition == MarketPosition.Short)
					ExitShort(0, Position.Quantity, "ExitOnClose", "");
				return;
			}

			// Don't open a new entry if one already exists.
			if (Position.MarketPosition != MarketPosition.Flat)
				return;

			// Re-entry guard: block any new entry this session if a prior trade already happened.
			if (PreventReentrySameSession && enteredThisSession)
				return;

			// Original direction-flag setting (preserved Tom3 logic).
			if (EMArange > EMArange1)
			{
				key1 = true;

				if (Close[0] < EMA200[0])
					Short = true;

				if (Close[0] > EMA200[0])
					Long = true;
			}

			if (EMArange > EMArange2)
			{
				// IMPORTANT: this intentionally preserves the original Tom3 direction-selection bug.
				bool bugWouldShort = Short && Long == true;
				bool bugWouldLong = !bugWouldShort;

				// Entry-permission filters — gate the entry without altering flag state.
				if (!HigherTimeframeTrendAllowsEntry(bugWouldLong, bugWouldShort))
				{
					DebugMessage("Entry blocked by HTF trend filter.");
					key1 = key2 = false;
					return;
				}

				if (!ATRRegimeAllowsEntry())
				{
					DebugMessage("Entry blocked by ATR regime filter.");
					key1 = key2 = false;
					return;
				}

				if (!OpeningRangeAllowsEntry(bugWouldLong, bugWouldShort))
				{
					DebugMessage("Entry blocked by opening-range filter.");
					key1 = key2 = false;
					return;
				}

				if (bugWouldShort)
				{
					EnterShort();
					Short = false;
					enteredThisSession = true;
					DebugMessage("EnterShort via preserved Tom3 bug logic. EMArange=" + EMArange);
				}
				else
				{
					EnterLong();
					Long = false;
					enteredThisSession = true;
					DebugMessage("EnterLong via preserved Tom3 bug logic. EMArange=" + EMArange);
				}

				key1 = key2 = false;
			}
		}

		// ----- Re-entry tracking -----

		private void TrackReentryState()
		{
			// If we transitioned from in-position to flat, the session has already had a trade.
			// enteredThisSession was already set true at entry; this keeps it true after exit
			// so PreventReentrySameSession works correctly across the rest of the session.
			lastMarketPosition = Position.MarketPosition;
		}

		// ----- Filters -----

		private bool HigherTimeframeTrendAllowsEntry(bool wouldLong, bool wouldShort)
		{
			if (!UseHigherTimeframeTrendFilter)
				return true;

			int slow = HigherTrendSlowEMA > 0 ? HigherTrendSlowEMA : 50;
			if (CurrentBars[1] < slow)
				return false;

			double fast = htfFast[0];
			double slowVal = htfSlow[0];

			bool htfUp = fast > slowVal;
			bool htfDown = fast < slowVal;

			if (wouldLong) return htfUp;
			if (wouldShort) return htfDown;
			return true;
		}

		private bool ATRRegimeAllowsEntry()
		{
			if (!UseATRRegimeFilter)
				return true;

			int baselinePeriod = ATRBaselinePeriod > 0 ? ATRBaselinePeriod : 50;
			int atrPeriod = ATRPeriod > 0 ? ATRPeriod : 14;
			if (CurrentBars[0] < baselinePeriod + atrPeriod)
				return false;

			double baseline = atrLongAvg[0];
			if (baseline <= 0)
				return false;

			double ratio = atrShort[0] / baseline;
			return ratio >= MinATRRatio && ratio <= MaxATRRatio;
		}

		private void UpdateOpeningRangeState()
		{
			if (!UseOpeningRangeConfirmation)
				return;

			int t = ToTime(Time[0]);

			if (t >= OpeningRangeStartTime && t < OpeningRangeEndTime)
			{
				if (High[0] > orHigh) orHigh = High[0];
				if (Low[0] < orLow) orLow = Low[0];
				return;
			}

			if (t >= OpeningRangeEndTime && orHigh > double.MinValue && orLow < double.MaxValue)
			{
				if (!orBreakoutLong && High[0] > orHigh)
					orBreakoutLong = true;
				if (!orBreakoutShort && Low[0] < orLow)
					orBreakoutShort = true;

				if (orBreakoutLong && !orRetestLong && Low[0] <= orHigh)
					orRetestLong = true;
				if (orBreakoutShort && !orRetestShort && High[0] >= orLow)
					orRetestShort = true;
			}
		}

		private bool OpeningRangeAllowsEntry(bool wouldLong, bool wouldShort)
		{
			if (!UseOpeningRangeConfirmation)
				return true;

			int t = ToTime(Time[0]);
			if (t < OpeningRangeEndTime) return false;
			if (orHigh <= double.MinValue || orLow >= double.MaxValue) return false;

			if (wouldLong)
				return RequireBreakoutRetest ? (orBreakoutLong && orRetestLong) : orBreakoutLong;

			if (wouldShort)
				return RequireBreakoutRetest ? (orBreakoutShort && orRetestShort) : orBreakoutShort;

			return true;
		}

		private void DebugMessage(string message)
		{
			if (EnableDebugPrint)
				Print(Time[0] + " | " + Name + " | " + message);
		}

		#region Properties

		// 01. Core Tom3 Parameters
		[NinjaScriptProperty]
		[Display(Name = "EMArange1", GroupName = "01. Core Tom3 Parameters", Order = 1)]
		public int EMArange1 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EMArange2", GroupName = "01. Core Tom3 Parameters", Order = 2)]
		public int EMArange2 { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "PreventReentrySameSession", GroupName = "01. Core Tom3 Parameters", Order = 3)]
		public bool PreventReentrySameSession { get; set; }

		// 02. Higher Timeframe Filter
		[NinjaScriptProperty]
		[Display(Name = "UseHigherTimeframeTrendFilter", GroupName = "02. Higher Timeframe Filter", Order = 10)]
		public bool UseHigherTimeframeTrendFilter { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "HigherTimeframeMinutes", GroupName = "02. Higher Timeframe Filter", Order = 11)]
		public int HigherTimeframeMinutes { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "HigherTrendFastEMA", GroupName = "02. Higher Timeframe Filter", Order = 12)]
		public int HigherTrendFastEMA { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "HigherTrendSlowEMA", GroupName = "02. Higher Timeframe Filter", Order = 13)]
		public int HigherTrendSlowEMA { get; set; }

		// 03. ATR Regime Filter
		[NinjaScriptProperty]
		[Display(Name = "UseATRRegimeFilter", GroupName = "03. ATR Regime Filter", Order = 20)]
		public bool UseATRRegimeFilter { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "ATRPeriod", GroupName = "03. ATR Regime Filter", Order = 21)]
		public int ATRPeriod { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "ATRBaselinePeriod", GroupName = "03. ATR Regime Filter", Order = 22)]
		public int ATRBaselinePeriod { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MinATRRatio", GroupName = "03. ATR Regime Filter", Order = 23)]
		public double MinATRRatio { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MaxATRRatio", GroupName = "03. ATR Regime Filter", Order = 24)]
		public double MaxATRRatio { get; set; }

		// 04. Opening Range Filter
		[NinjaScriptProperty]
		[Display(Name = "UseOpeningRangeConfirmation", GroupName = "04. Opening Range Filter", Order = 30)]
		public bool UseOpeningRangeConfirmation { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "OpeningRangeStartTime", GroupName = "04. Opening Range Filter", Order = 31)]
		public int OpeningRangeStartTime { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "OpeningRangeEndTime", GroupName = "04. Opening Range Filter", Order = 32)]
		public int OpeningRangeEndTime { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "RequireBreakoutRetest", GroupName = "04. Opening Range Filter", Order = 33)]
		public bool RequireBreakoutRetest { get; set; }

		// 05. Calendar Filter
		[NinjaScriptProperty]
		[Display(Name = "SkipSundayGlobex", GroupName = "05. Calendar Filter", Order = 40)]
		public bool SkipSundayGlobex { get; set; }

		// 06. Risk Wrapper
		[NinjaScriptProperty]
		[Display(Name = "UseCatastropheStopCurrency", GroupName = "06. Risk Wrapper", Order = 50)]
		public bool UseCatastropheStopCurrency { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "CatastropheStopCurrency", GroupName = "06. Risk Wrapper", Order = 51)]
		public double CatastropheStopCurrency { get; set; }

		// 99. Debug
		[NinjaScriptProperty]
		[Display(Name = "EnableDebugPrint", GroupName = "99. Debug", Order = 99)]
		public bool EnableDebugPrint { get; set; }

		#endregion
	}
}
