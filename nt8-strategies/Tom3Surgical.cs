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

// Tom3 Surgical — preserves Tom3's entry (including the direction-selection
// idiom) and adds nine independently-toggleable post-entry tactical rules,
// designed to attack the two distinct loser families:
//
//   Family A — early-failure losers
//   (down fast, MFE never meaningful, ride to close)
//   Rules: Early Failure Abort, No-Progress Time Stop, Early Adverse
//   Continuation, End-of-Session Damage Control.
//
//   Family B — profit-that-turned losers
//   (had real MFE, then reversed into losses)
//   Rules: MFE Breakeven Protection, Giveback Percent Exit, Two-Stage Stop.
//
//   Plus: Midnight long-danger filter (the recurring 00:00–00:15 long-loser
//   pattern) and Reduced-Size Bad-Regime Mode (rolling-50 PF size scaling).
//
// All rules default OFF. The baseline (everything off) equals raw Tom3 except
// PreventReentrySameSession which defaults to false — match raw Tom3 unless
// you specifically want one-trade-per-session.
//
// Run each rule alone first to measure its isolated effect. Combine only the
// rules that beat their own baseline on (loser-dollars-saved - winner-dollars-lost).
namespace NinjaTrader.NinjaScript.Strategies
{
	public class Tom3Surgical : Strategy
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

		// Per-trade tracking.
		private bool positionTrackingInitialized = false;
		private bool protectiveExitSubmitted = false;
		private DateTime entryTime = DateTime.MinValue;
		private int entryBarNumber = -1;
		private double signalPrice = 0;
		private double maxOpenProfitCurrency = 0;
		private double minOpenProfitCurrency = 0;
		private int consecutiveAdverseCloses = 0;
		private double tradeEntryPrice = 0;
		private MarketPosition lastMarketPosition = MarketPosition.Flat;

		// Session state.
		private bool tradeTakenThisSession = false;

		// Midnight delay state.
		private bool pendingMidnightLong = false;
		private DateTime pendingMidnightLongStartTime = DateTime.MinValue;
		private double pendingMidnightLongSignalPrice = 0;
		private double pendingMidnightLongSignalBarHigh = 0;

		// Cached rolling PF.
		private double currentSizeFraction = 1.0;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Tom3 with surgical post-entry tactical rules. Toggle each rule independently to test loser-family hypotheses. Preserves Tom3 entry idiom verbatim.";
				Name										= "Tom3 Surgical";
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

				// 01. Core Tom3 — match raw Tom3 baseline.
				EMArange1 = 40;
				EMArange2 = 70;
				PreventReentrySameSession = false;
				BaseQuantity = 1;

				// 02. Catastrophe stop (always-on safety; off by default to keep baseline clean).
				UseCatastropheStop = false;
				CatastropheStopCurrency = 15000;

				// 03. Early Failure Abort  (Family A)
				UseEarlyFailureAbort = false;
				EFA_MaxAdverseCurrency = 3500;
				EFA_LookbackMinutes = 120;
				EFA_RequireMFEBelow = 500;

				// 04. No-Progress Time Stop  (Family A)
				UseNoProgressTimeStop = false;
				NPTS_AfterHours = 4;
				NPTS_MinimumMFERequired = 1000;

				// 05. MFE Breakeven Protection  (Family B)
				UseMFEBreakevenProtection = false;
				MFEBE_ActivateAfterMFE = 2000;
				MFEBE_MinimumTimeBeforeProtectionMinutes = 60;
				MFEBE_ProtectedExitCurrency = 0;     // 0 = breakeven, -500 = -$500, +500 = +$500.

				// 06. Giveback Percent Exit  (Family B)
				UseGivebackPercentExit = false;
				GBP_ActivateAfterMFE = 3000;
				GBP_AllowedGivebackPct = 90;          // exits when current <= MFE * (1 - pct/100)

				// 07. Two-Stage Stop System  (Family B / Hybrid)
				UseTwoStageStopSystem = false;
				TSS_Stage2_MFETrigger = 2000;
				TSS_Stage2_MinAllowedCurrency = -500;   // becomes the floor after Stage2 triggers
				TSS_Stage3_MFETrigger = 5000;
				TSS_Stage3_MinAllowedCurrency = 1000;   // becomes the floor after Stage3 triggers

				// 08. Midnight Long Danger Filter  (Entry-side)
				UseMidnightLongDangerFilter = false;
				MNL_StartTime = 0;        // 00:00 HHMM
				MNL_EndTime = 15;         // 00:15 HHMM
				MNL_DelayMinutes = 30;
				MNL_RequireReclaimSignalBarHigh = true;

				// 09. Early Adverse Continuation Exit  (Family A)
				UseEarlyAdverseContinuation = false;
				EAC_ConsecutiveAdverseCloses = 5;
				EAC_MinimumLossCurrency = 1500;
				EAC_RequireMFEBelow = 500;

				// 10. End-of-Session Damage Control  (Family A)
				UseEndOfSessionDamageControl = false;
				EOS_MinutesBeforeClose = 60;
				EOS_ExitIfLossWorseThanCurrency = 2500;

				// 11. Reduced-Size Bad-Regime Mode  (Position-sizing)
				UseReducedSizeBadRegime = false;
				RSBR_RollingTrades = 50;
				RSBR_ReducePFThreshold = 1.10;
				RSBR_RestorePFThreshold = 1.30;
				RSBR_ReducedSizeFraction = 0.5;

				// 99. Debug
				EnableDebugPrint = false;
			}
			else if (State == State.Configure)
			{
				// No SetStopLoss / SetProfitTarget — all exits are currency-based and manual.
			}
			else if (State == State.DataLoaded)
			{
				EMA200 = EMA(Closes[0], 200);
				EMA5 = EMA(Closes[0], 20);
				AddChartIndicator(EMA200);
				AddChartIndicator(EMA5);
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

			// Existing Tom3 end-of-session flatten 180s before close.
			if (Time[0] >= sessionIterator.ActualSessionEnd.AddSeconds(-180)
				&& Time[0] <= sessionIterator.ActualSessionEnd)
			{
				if (Position.MarketPosition != MarketPosition.Flat && !protectiveExitSubmitted)
					SubmitProtectiveExit("ExitOnClose");
				return;
			}

			// Update rolling size based on recent PF before any entry decision.
			if (UseReducedSizeBadRegime)
				UpdateRollingSizeFraction();

			// Manage open trade.
			if (Position.MarketPosition != MarketPosition.Flat)
			{
				ManageOpenPosition();
				return;
			}
			else if (positionTrackingInitialized)
			{
				ResetTradeTrackingOnly();
			}

			// Pending midnight long delayed entry.
			if (UseMidnightLongDangerFilter && pendingMidnightLong)
			{
				EvaluatePendingMidnightLong();
				if (Position.MarketPosition != MarketPosition.Flat)
					return;
			}

			if (PreventReentrySameSession && tradeTakenThisSession)
				return;

			EMArange = Math.Abs(EMA200[0] - EMA5[0]);

			// Original Tom3 stage-one flag logic preserved.
			if (EMArange > EMArange1)
			{
				key1 = true;
				if (Close[0] < EMA200[0]) Short = true;
				if (Close[0] > EMA200[0]) Long = true;
			}

			// Original Tom3 entry trigger preserved with the direction-selection idiom.
			if (EMArange > EMArange2)
			{
				bool bugWouldShort = Short && Long == true;
				bool bugWouldLong = !bugWouldShort;

				// Midnight long danger filter — convert immediate long into a pending delayed long.
				if (UseMidnightLongDangerFilter && bugWouldLong && IsMidnightWindow(Time[0]))
				{
					pendingMidnightLong = true;
					pendingMidnightLongStartTime = Time[0];
					pendingMidnightLongSignalPrice = Close[0];
					pendingMidnightLongSignalBarHigh = High[0];
					Long = false;
					key1 = key2 = false;
					DebugLog("Midnight long deferred. Signal price=" + pendingMidnightLongSignalPrice
						+ " signal high=" + pendingMidnightLongSignalBarHigh);
					return;
				}

				if (bugWouldShort)
				{
					EnterShort(EntryQuantity(), "");
					Short = false;
					tradeTakenThisSession = true;
					DebugLog("EnterShort via preserved Tom3 idiom. EMArange=" + EMArange);
				}
				else
				{
					EnterLong(EntryQuantity(), "");
					Long = false;
					tradeTakenThisSession = true;
					DebugLog("EnterLong via preserved Tom3 idiom. EMArange=" + EMArange);
				}
				key1 = key2 = false;
			}
		}

		// ----- Position management — rules evaluated in priority order -----

		private void ManageOpenPosition()
		{
			if (!positionTrackingInitialized)
			{
				positionTrackingInitialized = true;
				protectiveExitSubmitted = false;
				entryTime = Time[0];
				entryBarNumber = CurrentBar;
				tradeEntryPrice = Position.AveragePrice;
				maxOpenProfitCurrency = 0;
				minOpenProfitCurrency = 0;
				consecutiveAdverseCloses = 0;
			}

			double openProfit = Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]);

			if (openProfit > maxOpenProfitCurrency)
				maxOpenProfitCurrency = openProfit;
			if (openProfit < minOpenProfitCurrency)
				minOpenProfitCurrency = openProfit;

			UpdateConsecutiveAdverseCounter();

			if (protectiveExitSubmitted)
				return;

			// 02. Catastrophe stop (highest priority — always-on safety).
			if (UseCatastropheStop && CatastropheStopCurrency > 0
				&& openProfit <= -CatastropheStopCurrency)
			{
				SubmitProtectiveExit("CatastropheStop");
				return;
			}

			// 03. Early Failure Abort.
			if (UseEarlyFailureAbort && Rule_EarlyFailureAbort(openProfit))
				return;

			// 04. No-Progress Time Stop.
			if (UseNoProgressTimeStop && Rule_NoProgressTimeStop(openProfit))
				return;

			// 07. Two-Stage Stop System.
			if (UseTwoStageStopSystem && Rule_TwoStageStop(openProfit))
				return;

			// 05. MFE Breakeven Protection.
			if (UseMFEBreakevenProtection && Rule_MFEBreakeven(openProfit))
				return;

			// 06. Giveback Percent Exit.
			if (UseGivebackPercentExit && Rule_GivebackPercent(openProfit))
				return;

			// 09. Early Adverse Continuation.
			if (UseEarlyAdverseContinuation && Rule_EarlyAdverseContinuation(openProfit))
				return;

			// 10. End-of-Session Damage Control.
			if (UseEndOfSessionDamageControl && Rule_EndOfSessionDamageControl(openProfit))
				return;
		}

		// ----- Rule implementations -----

		private bool Rule_EarlyFailureAbort(double openProfit)
		{
			double minutesInTrade = MinutesInTrade();
			if (minutesInTrade > EFA_LookbackMinutes) return false;
			if (openProfit > -EFA_MaxAdverseCurrency) return false;
			if (maxOpenProfitCurrency >= EFA_RequireMFEBelow) return false;

			SubmitProtectiveExit("EarlyFailureAbort");
			return true;
		}

		private bool Rule_NoProgressTimeStop(double openProfit)
		{
			double hoursInTrade = MinutesInTrade() / 60.0;
			if (hoursInTrade < NPTS_AfterHours) return false;
			if (openProfit >= 0) return false;
			if (maxOpenProfitCurrency >= NPTS_MinimumMFERequired) return false;

			SubmitProtectiveExit("NoProgressTimeStop");
			return true;
		}

		private bool Rule_MFEBreakeven(double openProfit)
		{
			if (maxOpenProfitCurrency < MFEBE_ActivateAfterMFE) return false;
			if (MinutesInTrade() < MFEBE_MinimumTimeBeforeProtectionMinutes) return false;
			if (openProfit > MFEBE_ProtectedExitCurrency) return false;

			SubmitProtectiveExit("MFEBreakeven");
			return true;
		}

		private bool Rule_GivebackPercent(double openProfit)
		{
			if (maxOpenProfitCurrency < GBP_ActivateAfterMFE) return false;
			double allowedGiveback = maxOpenProfitCurrency * (GBP_AllowedGivebackPct / 100.0);
			double floor = maxOpenProfitCurrency - allowedGiveback;
			if (openProfit > floor) return false;

			SubmitProtectiveExit("GivebackPct");
			return true;
		}

		private bool Rule_TwoStageStop(double openProfit)
		{
			// Stage 3: most protective, applies if MFE peaked above stage-3 trigger.
			if (maxOpenProfitCurrency >= TSS_Stage3_MFETrigger)
			{
				if (openProfit <= TSS_Stage3_MinAllowedCurrency)
				{
					SubmitProtectiveExit("TwoStageStop_S3");
					return true;
				}
				return false;
			}

			// Stage 2: applies if MFE peaked above stage-2 trigger.
			if (maxOpenProfitCurrency >= TSS_Stage2_MFETrigger)
			{
				if (openProfit <= TSS_Stage2_MinAllowedCurrency)
				{
					SubmitProtectiveExit("TwoStageStop_S2");
					return true;
				}
				return false;
			}

			// Stage 1: no stop here — relies on catastrophe stop if also enabled.
			return false;
		}

		private bool Rule_EarlyAdverseContinuation(double openProfit)
		{
			if (consecutiveAdverseCloses < EAC_ConsecutiveAdverseCloses) return false;
			if (openProfit > -EAC_MinimumLossCurrency) return false;
			if (maxOpenProfitCurrency >= EAC_RequireMFEBelow) return false;

			SubmitProtectiveExit("EarlyAdverseContinuation");
			return true;
		}

		private bool Rule_EndOfSessionDamageControl(double openProfit)
		{
			double minutesToClose = sessionIterator.ActualSessionEnd.Subtract(Time[0]).TotalMinutes;
			if (minutesToClose > EOS_MinutesBeforeClose) return false;
			if (openProfit > -EOS_ExitIfLossWorseThanCurrency) return false;

			SubmitProtectiveExit("EndOfSessionDamageCtl");
			return true;
		}

		// ----- Helpers -----

		private void UpdateConsecutiveAdverseCounter()
		{
			bool adverseClose = (Position.MarketPosition == MarketPosition.Long && Close[0] < tradeEntryPrice)
				|| (Position.MarketPosition == MarketPosition.Short && Close[0] > tradeEntryPrice);

			if (adverseClose) consecutiveAdverseCloses++;
			else consecutiveAdverseCloses = 0;
		}

		private double MinutesInTrade()
		{
			if (entryTime == DateTime.MinValue) return 0;
			return Time[0].Subtract(entryTime).TotalMinutes;
		}

		private bool IsMidnightWindow(DateTime t)
		{
			int hhmm = t.Hour * 100 + t.Minute;
			return hhmm >= MNL_StartTime && hhmm <= MNL_EndTime;
		}

		private void EvaluatePendingMidnightLong()
		{
			double minutesElapsed = Time[0].Subtract(pendingMidnightLongStartTime).TotalMinutes;
			if (minutesElapsed < MNL_DelayMinutes)
				return;

			bool conditionMet =
				MNL_RequireReclaimSignalBarHigh
					? Close[0] >= pendingMidnightLongSignalBarHigh
					: Close[0] >= pendingMidnightLongSignalPrice;

			if (conditionMet)
			{
				EnterLong(EntryQuantity(), "");
				tradeTakenThisSession = true;
				DebugLog("MidnightLong delayed-entry triggered after " + minutesElapsed + " min.");
			}
			else
			{
				DebugLog("MidnightLong delayed-entry abandoned (condition not met after "
					+ minutesElapsed + " min, current=" + Close[0]
					+ " required>=" + (MNL_RequireReclaimSignalBarHigh ? pendingMidnightLongSignalBarHigh : pendingMidnightLongSignalPrice) + ").");
			}

			pendingMidnightLong = false;
		}

		private int EntryQuantity()
		{
			int q = (int)Math.Round(BaseQuantity * currentSizeFraction);
			return q < 1 ? 1 : q;
		}

		private void UpdateRollingSizeFraction()
		{
			var trades = SystemPerformance.AllTrades;
			int count = trades.Count;
			if (count < RSBR_RollingTrades)
			{
				currentSizeFraction = 1.0;
				return;
			}

			double gross = 0, loss = 0;
			int start = count - RSBR_RollingTrades;
			for (int i = start; i < count; i++)
			{
				double pnl = trades[i].ProfitCurrency;
				if (pnl > 0) gross += pnl;
				else loss -= pnl;
			}
			double pf = (loss > 0) ? (gross / loss) : (gross > 0 ? double.PositiveInfinity : 1.0);

			if (currentSizeFraction < 1.0)
			{
				// Currently reduced — restore only if PF recovers past restore threshold.
				if (pf >= RSBR_RestorePFThreshold)
					currentSizeFraction = 1.0;
			}
			else
			{
				// Currently full — reduce if PF drops below reduce threshold.
				if (pf < RSBR_ReducePFThreshold)
					currentSizeFraction = RSBR_ReducedSizeFraction;
			}
		}

		// ----- Plumbing -----

		private void SubmitProtectiveExit(string signalName)
		{
			protectiveExitSubmitted = true;
			DebugLog(signalName + " | OpenPnL=" + Position.GetUnrealizedProfitLoss(PerformanceUnit.Currency, Close[0]).ToString("F2")
				+ " | MFE=" + maxOpenProfitCurrency.ToString("F2")
				+ " | MAE=" + minOpenProfitCurrency.ToString("F2")
				+ " | MinutesInTrade=" + MinutesInTrade().ToString("F0")
				+ " | Pos=" + Position.MarketPosition.ToString());

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
			pendingMidnightLong = false;
			ResetTradeTrackingOnly();
		}

		private void ResetTradeTrackingOnly()
		{
			positionTrackingInitialized = false;
			protectiveExitSubmitted = false;
			entryTime = DateTime.MinValue;
			entryBarNumber = -1;
			tradeEntryPrice = 0;
			maxOpenProfitCurrency = 0;
			minOpenProfitCurrency = 0;
			consecutiveAdverseCloses = 0;
		}

		private void DebugLog(string message)
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

		[NinjaScriptProperty]
		[Display(Name = "BaseQuantity", GroupName = "01. Core Tom3 Parameters", Order = 4)]
		public int BaseQuantity { get; set; }

		// 02. Catastrophe Stop
		[NinjaScriptProperty]
		[Display(Name = "UseCatastropheStop", GroupName = "02. Catastrophe Stop", Order = 10)]
		public bool UseCatastropheStop { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "CatastropheStopCurrency", GroupName = "02. Catastrophe Stop", Order = 11)]
		public double CatastropheStopCurrency { get; set; }

		// 03. Early Failure Abort  (Family A)
		[NinjaScriptProperty]
		[Display(Name = "UseEarlyFailureAbort", Description = "Family A. Abort if down >MaxAdverse within LookbackMinutes AND MFE never reached RequireMFEBelow.", GroupName = "03. Early Failure Abort (Family A)", Order = 20)]
		public bool UseEarlyFailureAbort { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EFA_MaxAdverseCurrency", GroupName = "03. Early Failure Abort (Family A)", Order = 21)]
		public double EFA_MaxAdverseCurrency { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EFA_LookbackMinutes", GroupName = "03. Early Failure Abort (Family A)", Order = 22)]
		public int EFA_LookbackMinutes { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EFA_RequireMFEBelow", GroupName = "03. Early Failure Abort (Family A)", Order = 23)]
		public double EFA_RequireMFEBelow { get; set; }

		// 04. No-Progress Time Stop  (Family A)
		[NinjaScriptProperty]
		[Display(Name = "UseNoProgressTimeStop", Description = "Family A. Exit after AfterHours if current PnL<0 AND MFE never reached MinimumMFERequired.", GroupName = "04. No-Progress Time Stop (Family A)", Order = 30)]
		public bool UseNoProgressTimeStop { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "NPTS_AfterHours", GroupName = "04. No-Progress Time Stop (Family A)", Order = 31)]
		public double NPTS_AfterHours { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "NPTS_MinimumMFERequired", GroupName = "04. No-Progress Time Stop (Family A)", Order = 32)]
		public double NPTS_MinimumMFERequired { get; set; }

		// 05. MFE Breakeven Protection  (Family B)
		[NinjaScriptProperty]
		[Display(Name = "UseMFEBreakevenProtection", Description = "Family B. Once MFE reaches ActivateAfterMFE and time>=MinTime, exit at ProtectedExit.", GroupName = "05. MFE Breakeven Protection (Family B)", Order = 40)]
		public bool UseMFEBreakevenProtection { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MFEBE_ActivateAfterMFE", GroupName = "05. MFE Breakeven Protection (Family B)", Order = 41)]
		public double MFEBE_ActivateAfterMFE { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MFEBE_MinimumTimeBeforeProtectionMinutes", GroupName = "05. MFE Breakeven Protection (Family B)", Order = 42)]
		public int MFEBE_MinimumTimeBeforeProtectionMinutes { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MFEBE_ProtectedExitCurrency", Description = "Exit floor in $. 0=breakeven, -500=$-500, 500=$+500.", GroupName = "05. MFE Breakeven Protection (Family B)", Order = 43)]
		public double MFEBE_ProtectedExitCurrency { get; set; }

		// 06. Giveback Percent Exit  (Family B)
		[NinjaScriptProperty]
		[Display(Name = "UseGivebackPercentExit", Description = "Family B. Once MFE reaches ActivateAfterMFE, exit if giveback exceeds AllowedGivebackPct of MFE.", GroupName = "06. Giveback Percent Exit (Family B)", Order = 50)]
		public bool UseGivebackPercentExit { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "GBP_ActivateAfterMFE", GroupName = "06. Giveback Percent Exit (Family B)", Order = 51)]
		public double GBP_ActivateAfterMFE { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "GBP_AllowedGivebackPct", Description = "Percent of MFE allowed to be given back. 90 = 90%.", GroupName = "06. Giveback Percent Exit (Family B)", Order = 52)]
		public double GBP_AllowedGivebackPct { get; set; }

		// 07. Two-Stage Stop System
		[NinjaScriptProperty]
		[Display(Name = "UseTwoStageStopSystem", Description = "Family B. Tightens floor as MFE crosses Stage2 then Stage3 triggers.", GroupName = "07. Two-Stage Stop System", Order = 60)]
		public bool UseTwoStageStopSystem { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "TSS_Stage2_MFETrigger", GroupName = "07. Two-Stage Stop System", Order = 61)]
		public double TSS_Stage2_MFETrigger { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "TSS_Stage2_MinAllowedCurrency", GroupName = "07. Two-Stage Stop System", Order = 62)]
		public double TSS_Stage2_MinAllowedCurrency { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "TSS_Stage3_MFETrigger", GroupName = "07. Two-Stage Stop System", Order = 63)]
		public double TSS_Stage3_MFETrigger { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "TSS_Stage3_MinAllowedCurrency", GroupName = "07. Two-Stage Stop System", Order = 64)]
		public double TSS_Stage3_MinAllowedCurrency { get; set; }

		// 08. Midnight Long Danger Filter
		[NinjaScriptProperty]
		[Display(Name = "UseMidnightLongDangerFilter", Description = "Entry. Delay long entries in 00:00-00:15 by DelayMinutes; require reclaim of signal price or signal bar high.", GroupName = "08. Midnight Long Danger Filter", Order = 70)]
		public bool UseMidnightLongDangerFilter { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MNL_StartTime", Description = "HHMM, e.g. 0 = 00:00.", GroupName = "08. Midnight Long Danger Filter", Order = 71)]
		public int MNL_StartTime { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MNL_EndTime", Description = "HHMM, e.g. 15 = 00:15.", GroupName = "08. Midnight Long Danger Filter", Order = 72)]
		public int MNL_EndTime { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MNL_DelayMinutes", GroupName = "08. Midnight Long Danger Filter", Order = 73)]
		public int MNL_DelayMinutes { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "MNL_RequireReclaimSignalBarHigh", GroupName = "08. Midnight Long Danger Filter", Order = 74)]
		public bool MNL_RequireReclaimSignalBarHigh { get; set; }

		// 09. Early Adverse Continuation
		[NinjaScriptProperty]
		[Display(Name = "UseEarlyAdverseContinuation", Description = "Family A. Exit after N consecutive adverse closes if loss>Min and MFE<RequireBelow.", GroupName = "09. Early Adverse Continuation (Family A)", Order = 80)]
		public bool UseEarlyAdverseContinuation { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EAC_ConsecutiveAdverseCloses", GroupName = "09. Early Adverse Continuation (Family A)", Order = 81)]
		public int EAC_ConsecutiveAdverseCloses { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EAC_MinimumLossCurrency", GroupName = "09. Early Adverse Continuation (Family A)", Order = 82)]
		public double EAC_MinimumLossCurrency { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EAC_RequireMFEBelow", GroupName = "09. Early Adverse Continuation (Family A)", Order = 83)]
		public double EAC_RequireMFEBelow { get; set; }

		// 10. End-of-Session Damage Control
		[NinjaScriptProperty]
		[Display(Name = "UseEndOfSessionDamageControl", Description = "Family A. In last X minutes of session, exit early if current PnL worse than threshold.", GroupName = "10. End-of-Session Damage Control (Family A)", Order = 90)]
		public bool UseEndOfSessionDamageControl { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EOS_MinutesBeforeClose", GroupName = "10. End-of-Session Damage Control (Family A)", Order = 91)]
		public int EOS_MinutesBeforeClose { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EOS_ExitIfLossWorseThanCurrency", GroupName = "10. End-of-Session Damage Control (Family A)", Order = 92)]
		public double EOS_ExitIfLossWorseThanCurrency { get; set; }

		// 11. Reduced-Size Bad Regime Mode
		[NinjaScriptProperty]
		[Display(Name = "UseReducedSizeBadRegime", Description = "Size. If rolling-N PF < Reduce threshold, scale entry quantity by Fraction. Restore when PF >= Restore threshold.", GroupName = "11. Reduced-Size Bad Regime Mode", Order = 100)]
		public bool UseReducedSizeBadRegime { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "RSBR_RollingTrades", GroupName = "11. Reduced-Size Bad Regime Mode", Order = 101)]
		public int RSBR_RollingTrades { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "RSBR_ReducePFThreshold", GroupName = "11. Reduced-Size Bad Regime Mode", Order = 102)]
		public double RSBR_ReducePFThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "RSBR_RestorePFThreshold", GroupName = "11. Reduced-Size Bad Regime Mode", Order = 103)]
		public double RSBR_RestorePFThreshold { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "RSBR_ReducedSizeFraction", Description = "0.5 = half size when regime is bad.", GroupName = "11. Reduced-Size Bad Regime Mode", Order = 104)]
		public double RSBR_ReducedSizeFraction { get; set; }

		// 99. Debug
		[NinjaScriptProperty]
		[Display(Name = "EnableDebugPrint", GroupName = "99. Debug", Order = 99)]
		public bool EnableDebugPrint { get; set; }

		#endregion
	}
}
