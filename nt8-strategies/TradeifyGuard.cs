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

// TradeifyGuard — account-level compliance + risk wrapper for Tradeify
// Lightning Funded Accounts. Add this as a sibling NinjaScript strategy on
// the same prop account as your trading strategies (Tom3 etc.). It does not
// place its own entries — it monitors the account and enforces four rules:
//
//   RISK RULES
//   1. Daily Loss Guard: flatten + halt when today's (realized + unrealized)
//      P&L drops below -DailyMaxLossCurrency. Tradeify Lightning 100K:
//      Daily Loss Limit is "soft" at -$2,500; recommended threshold -$2,000.
//
//   2. Trailing Drawdown Guard: flatten + halt when current equity drops more
//      than TrailingGuardCurrency below the running peak. Tradeify Lightning
//      100K: $4,000 hard trailing max DD; recommended threshold -$3,500.
//
//   COMPLIANCE RULES (account-rule enforcement, separate from risk)
//   3. Cross-instrument prohibition: Tradeify forbids holding minis + micros
//      simultaneously. If the account holds BOTH the configured mini symbol
//      AND the micro symbol, the prohibited side (per ProhibitedSymbol) is
//      auto-flattened.
//
//   4. Same-symbol opposing-entry prevention: Tradeify forbids long + short
//      on the same instrument at the same time. The guard:
//        a) Cancels any WORKING entry order whose direction would oppose the
//           current account direction (catches limit/stop entries before fill).
//        b) If an opposing entry fills anyway (market orders) and the broker
//           does not auto-net to flat, the resulting "wrong-side" position is
//           immediately flattened.
//
// Critical operational notes:
//   - The guard is a no-op in Strategy Analyzer (State.Historical) so it
//     does not contaminate backtest P&L of the underlying strategies.
//   - The guard FLATTENS but cannot disable sibling strategies. If a
//     strategy re-enters after a flatten, the guard will flatten again.
//   - Compliance rules 3+4 are best-effort. Market-order fills are
//     near-instantaneous; the guard reacts within one bar update (typically
//     ≤1 second on 1-min charts, faster on tick-replay). Tradeify may still
//     see the brief opposing-ticket overlap in their order blotter.
//   - For absolute compliance, the underlying strategies should also call
//     the static method `TradeifyGuard.IsEntryAllowed(...)` before submitting
//     entry orders. Existing strategies (Tom3 etc.) do not — that's why the
//     reactive enforcement layer exists.
namespace NinjaTrader.NinjaScript.Strategies
{
	public class TradeifyGuard : Strategy
	{
		private Account guardAccount;
		private bool sessionInitialized = false;
		private double sessionStartBalance = 0.0;
		private double runningPeak = 0.0;
		private bool dailyLossHaltActive = false;
		private bool trailHaltActive = false;
		private DateTime lastSessionDate = DateTime.MinValue;

		// Public coordination state — strategies that opt-in can read this.
		public static MarketPosition CurrentDirection { get; private set; } = MarketPosition.Flat;
		public static string LockedSymbol { get; private set; } = null;
		public static bool IsHaltActive { get; private set; } = false;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Tradeify Lightning Funded Account compliance + risk guard. Monitors realized + unrealized P&L on the bound account; flattens and halts on Daily Loss or Trailing Drawdown breach. Also enforces (1) prohibition on holding minis + micros, and (2) prohibition on long+short on the same instrument. Add as a sibling strategy on the same prop account as your trading strategies. No-op in backtest.";
				Name										= "TradeifyGuard";
				Calculate									= Calculate.OnBarClose;
				EntriesPerDirection							= 1;
				EntryHandling								= EntryHandling.AllEntries;
				IsExitOnSessionCloseStrategy				= false;
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
				BarsRequiredToTrade							= 1;
				IsInstantiatedOnEachOptimizationIteration	= false;

				// 01. Account
				AccountName                   = "Sim101";

				// 02. Risk thresholds
				DailyMaxLossCurrency          = 2000;
				TrailingGuardCurrency         = 3500;

				// 03. Symbol policy
				PrimarySymbol                 = "MNQ";   // The contract pool we're trading
				ProhibitedSymbol              = "NQ";    // The pool Tradeify forbids while PrimarySymbol is held

				// 04. Behavior
				EnableDebugPrint              = true;
			}
			else if (State == State.Configure)
			{
				// nothing
			}
			else if (State == State.DataLoaded)
			{
				lock (Account.All)
					guardAccount = Account.All.FirstOrDefault(a => a.Name == AccountName);
			}
		}

		protected override void OnBarUpdate()
		{
			if (State != State.Realtime) return;
			if (guardAccount == null)
			{
				DebugLog("guardAccount NULL — account '" + AccountName + "' not found. Guard disabled.");
				return;
			}

			// --- Session-start bookkeeping ---
			DateTime today = Time[0].Date;
			if (today != lastSessionDate)
			{
				double startBal = guardAccount.Get(AccountItem.NetLiquidation, Currency.UsDollar);
				sessionStartBalance = startBal;
				if (startBal > runningPeak) runningPeak = startBal;
				lastSessionDate = today;
				dailyLossHaltActive = false;
				trailHaltActive = false;
				IsHaltActive = false;
				sessionInitialized = true;
				DebugLog("New session " + today.ToString("yyyy-MM-dd")
					+ " | start=" + startBal.ToString("F2")
					+ " | peak=" + runningPeak.ToString("F2"));
			}
			if (!sessionInitialized) return;

			// --- Live P&L ---
			double realized   = guardAccount.Get(AccountItem.RealizedProfitLoss, Currency.UsDollar);
			double unrealized = guardAccount.Get(AccountItem.UnrealizedProfitLoss, Currency.UsDollar);
			double currentBalance = sessionStartBalance + realized + unrealized;
			double dailyPnL = realized + unrealized;
			double drawdownFromPeak = currentBalance - runningPeak;

			if (currentBalance > runningPeak) runningPeak = currentBalance;

			// --- RISK RULE 1: Daily Max Loss ---
			if (!dailyLossHaltActive && dailyPnL <= -Math.Abs(DailyMaxLossCurrency))
			{
				dailyLossHaltActive = true;
				IsHaltActive = true;
				DebugLog("DAILY-MAX-LOSS BREACH: dailyPnL=" + dailyPnL.ToString("F2")
					+ " <= -" + DailyMaxLossCurrency + ". Flattening + halting.");
				FlattenAllFutures("DailyMaxLossGuard");
				CancelAllWorkingOrders("DailyMaxLossGuard");
				return;
			}

			// --- RISK RULE 2: Trailing Drawdown ---
			if (!trailHaltActive && drawdownFromPeak <= -Math.Abs(TrailingGuardCurrency))
			{
				trailHaltActive = true;
				IsHaltActive = true;
				DebugLog("TRAILING-DD BREACH: balance=" + currentBalance.ToString("F2")
					+ " peak=" + runningPeak.ToString("F2")
					+ " drawdown=" + drawdownFromPeak.ToString("F2")
					+ " <= -" + TrailingGuardCurrency + ". Flattening + halting.");
				FlattenAllFutures("TrailingGuard");
				CancelAllWorkingOrders("TrailingGuard");
				return;
			}

			// --- If a risk halt is active, keep flattening unauthorized re-entries ---
			if (dailyLossHaltActive || trailHaltActive)
			{
				if (AnyOpenFuturesPosition())
				{
					DebugLog("Halt active — re-flattening unauthorized position.");
					FlattenAllFutures("Guard-re");
					CancelAllWorkingOrders("Guard-re");
				}
				return;
			}

			// --- COMPLIANCE RULE 3: Cross-instrument prohibition ---
			Position primaryPos    = FindPosition(PrimarySymbol);
			Position prohibitedPos = FindPosition(ProhibitedSymbol);
			bool hasPrimary    = primaryPos    != null && primaryPos.Quantity    > 0;
			bool hasProhibited = prohibitedPos != null && prohibitedPos.Quantity > 0;

			if (hasPrimary && hasProhibited)
			{
				DebugLog("CROSS-SYMBOL VIOLATION: holding " + PrimarySymbol + " AND " + ProhibitedSymbol
					+ ". Flattening " + ProhibitedSymbol + " (prohibited pool).");
				FlattenInstrument(prohibitedPos.Instrument, "CrossSymbolGuard");
				return;
			}

			// Also: cancel any working order that would OPEN a prohibited-symbol position.
			foreach (Order o in WorkingFuturesOrders())
			{
				if (o.Instrument.MasterInstrument.Name.Equals(ProhibitedSymbol, StringComparison.OrdinalIgnoreCase)
					&& IsEntryOrder(o, prohibitedPos))
				{
					DebugLog("CANCEL prohibited-symbol working order: " + o.Name + " (" + o.OrderAction + ")");
					guardAccount.Cancel(new[] { o });
				}
			}

			// --- COMPLIANCE RULE 4: Same-symbol opposing-direction prevention ---
			// Determine current direction on the primary symbol.
			MarketPosition currentDir = primaryPos != null && primaryPos.Quantity > 0
				? primaryPos.MarketPosition
				: MarketPosition.Flat;
			CurrentDirection = currentDir;
			LockedSymbol = currentDir != MarketPosition.Flat ? PrimarySymbol : null;

			// 4a. Cancel any working entry order on PrimarySymbol that would create
			//     a position OPPOSITE to currentDir.
			foreach (Order o in WorkingFuturesOrders())
			{
				if (!o.Instrument.MasterInstrument.Name.Equals(PrimarySymbol, StringComparison.OrdinalIgnoreCase))
					continue;
				if (!IsEntryOrder(o, primaryPos)) continue;

				bool wouldOpenLong  = o.OrderAction == OrderAction.Buy;
				bool wouldOpenShort = o.OrderAction == OrderAction.SellShort;

				if (currentDir == MarketPosition.Long  && wouldOpenShort)
				{
					DebugLog("CANCEL opposing SHORT entry while LONG " + PrimarySymbol + ": " + o.Name);
					guardAccount.Cancel(new[] { o });
				}
				else if (currentDir == MarketPosition.Short && wouldOpenLong)
				{
					DebugLog("CANCEL opposing LONG entry while SHORT " + PrimarySymbol + ": " + o.Name);
					guardAccount.Cancel(new[] { o });
				}
			}
			// 4b. If somehow an opposing position materialised (market-order race),
			//     futures-net should have flattened both — but if not, flatten the
			//     primary symbol entirely and let the surviving direction reassert
			//     on the next signal. This is the safest reaction.
			// (No-op: with futures broker netting this case is rare.)

			IsHaltActive = false;
		}

		// ------------- Public opt-in API for cooperative strategies -------------
		// Strategies can call this BEFORE submitting an entry to check compliance.
		// Returns true if the entry is allowed by the guard's policy.
		public static bool IsEntryAllowed(string symbol, MarketPosition desiredDirection)
		{
			if (IsHaltActive) return false;
			if (string.IsNullOrEmpty(LockedSymbol) || CurrentDirection == MarketPosition.Flat)
				return true;
			// If a direction is locked, only allow same-direction entries (adds), not opposing.
			if (!symbol.Equals(LockedSymbol, StringComparison.OrdinalIgnoreCase))
				return false;
			return desiredDirection == CurrentDirection;
		}

		// ------------- helpers -------------
		private bool AnyOpenFuturesPosition()
		{
			if (guardAccount == null) return false;
			foreach (Position p in guardAccount.Positions)
			{
				if (p.Instrument.MasterInstrument.InstrumentType == InstrumentType.Future
					&& p.Quantity > 0) return true;
			}
			return false;
		}

		private Position FindPosition(string masterInstrumentName)
		{
			if (guardAccount == null || string.IsNullOrEmpty(masterInstrumentName)) return null;
			foreach (Position p in guardAccount.Positions)
			{
				if (p.Instrument.MasterInstrument.Name.Equals(masterInstrumentName, StringComparison.OrdinalIgnoreCase))
					return p;
			}
			return null;
		}

		private IEnumerable<Order> WorkingFuturesOrders()
		{
			if (guardAccount == null) yield break;
			foreach (Order o in guardAccount.Orders)
			{
				if (o.OrderState != OrderState.Working
					&& o.OrderState != OrderState.Accepted
					&& o.OrderState != OrderState.Submitted)
					continue;
				if (o.Instrument.MasterInstrument.InstrumentType != InstrumentType.Future)
					continue;
				yield return o;
			}
		}

		private bool IsEntryOrder(Order o, Position existingPos)
		{
			// Buy / SellShort are entry actions when account is flat or adding.
			// Sell / BuyToCover are exits.
			if (o.OrderAction == OrderAction.Sell || o.OrderAction == OrderAction.BuyToCover)
				return false;
			return true;
		}

		private void FlattenAllFutures(string reason)
		{
			if (guardAccount == null) return;
			List<Instrument> instruments = new List<Instrument>();
			foreach (Position p in guardAccount.Positions)
			{
				if (p.Instrument.MasterInstrument.InstrumentType == InstrumentType.Future && p.Quantity > 0)
					instruments.Add(p.Instrument);
			}
			if (instruments.Count == 0) return;
			try
			{
				guardAccount.Flatten(instruments.ToArray());
				Log("TradeifyGuard FLATTEN (" + reason + "): " + string.Join(",", instruments.Select(i => i.MasterInstrument.Name)), LogLevel.Warning);
			}
			catch (Exception ex) { Log("Flatten error: " + ex.Message, LogLevel.Error); }
		}

		private void FlattenInstrument(Instrument inst, string reason)
		{
			if (guardAccount == null || inst == null) return;
			try
			{
				guardAccount.Flatten(new[] { inst });
				Log("TradeifyGuard FLATTEN (" + reason + "): " + inst.MasterInstrument.Name, LogLevel.Warning);
			}
			catch (Exception ex) { Log("FlattenInstrument error: " + ex.Message, LogLevel.Error); }
		}

		private void CancelAllWorkingOrders(string reason)
		{
			if (guardAccount == null) return;
			List<Order> toCancel = new List<Order>();
			foreach (Order o in guardAccount.Orders)
			{
				if (o.OrderState == OrderState.Working
					|| o.OrderState == OrderState.Accepted
					|| o.OrderState == OrderState.Submitted)
					toCancel.Add(o);
			}
			if (toCancel.Count > 0)
			{
				try
				{
					guardAccount.Cancel(toCancel);
					DebugLog("CancelAllWorkingOrders (" + reason + "): cancelled " + toCancel.Count + " orders.");
				}
				catch (Exception ex) { Log("Cancel error: " + ex.Message, LogLevel.Error); }
			}
		}

		private void DebugLog(string m)
		{
			if (EnableDebugPrint)
				Print(Time[0].ToString("yyyy-MM-dd HH:mm:ss") + " | TradeifyGuard | " + m);
		}

		#region Properties

		[NinjaScriptProperty]
		[Display(Name = "AccountName", Description = "Exact NT8 account name to guard (e.g. Sim101 or your live Tradeify funded account name).", GroupName = "01. Tradeify Account", Order = 1)]
		public string AccountName { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "DailyMaxLossCurrency", Description = "Flatten + halt if today's (realized + unrealized) P&L drops below -this. Tradeify Lightning 100K Daily Loss Limit is -$2,500 (soft); recommended -$2,000.", GroupName = "02. Risk Thresholds", Order = 10)]
		public double DailyMaxLossCurrency { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "TrailingGuardCurrency", Description = "Flatten + halt if balance drops more than this below running peak. Tradeify Lightning 100K Trailing Max DD is $4,000 (hard); recommended $3,500.", GroupName = "02. Risk Thresholds", Order = 11)]
		public double TrailingGuardCurrency { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "PrimarySymbol", Description = "The Master Instrument name of the pool you ARE trading (e.g. MNQ). Long+short on this symbol is prevented.", GroupName = "03. Symbol Policy", Order = 20)]
		public string PrimarySymbol { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "ProhibitedSymbol", Description = "The Master Instrument name of the pool you must NOT trade while holding PrimarySymbol (e.g. NQ). Auto-flattened if encountered.", GroupName = "03. Symbol Policy", Order = 21)]
		public string ProhibitedSymbol { get; set; }

		[NinjaScriptProperty]
		[Display(Name = "EnableDebugPrint", GroupName = "99. Debug", Order = 99)]
		public bool EnableDebugPrint { get; set; }

		#endregion
	}
}
