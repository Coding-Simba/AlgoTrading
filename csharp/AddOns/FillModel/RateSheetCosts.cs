using System;

namespace AlgoTrading.FillModel
{
    public sealed class RateSheetError : Exception
    {
        public RateSheetError(string message) : base(message) { }
    }

    /// <summary>
    /// Real-cost model. Replaces PlaceholderCosts once Ops signs the rate
    /// sheet (errata §5). A RateSheetCosts instance produces fills with
    /// Tag="" (empty), so any fill stream sourced from it is NOT rejected
    /// by the approved-backtest guard.
    ///
    /// Constructor enforces the invariants from rate_sheet_costs.py.
    /// YAML loading is deferred to Configs/ (task #3).
    /// </summary>
    public sealed class RateSheetCosts : ICosts
    {
        public string Instrument { get; }
        public int CommissionPerSideUsdCents { get; }
        public int AllInPerSideUsdCents { get; }
        public int TickValueUsdCents { get; }
        public int SlippageTicks { get; }
        public string Tag { get; }

        public int CommissionPerSideTicks =>
            (int)Math.Ceiling(AllInPerSideUsdCents / (double)TickValueUsdCents);

        public RateSheetCosts(
            string instrument,
            int commissionPerSideUsdCents,
            int allInPerSideUsdCents,
            int tickValueUsdCents,
            int slippageTicks)
        {
            if (commissionPerSideUsdCents < 0) throw new RateSheetError("commission must be >= 0");
            if (allInPerSideUsdCents < 0)      throw new RateSheetError("all_in_per_side must be >= 0");
            if (tickValueUsdCents <= 0)        throw new RateSheetError("tick_value must be > 0");
            if (slippageTicks < 0)             throw new RateSheetError("slippage_ticks must be >= 0");

            Instrument = instrument;
            CommissionPerSideUsdCents = commissionPerSideUsdCents;
            AllInPerSideUsdCents = allInPerSideUsdCents;
            TickValueUsdCents = tickValueUsdCents;
            SlippageTicks = slippageTicks;
            Tag = ""; // never D2_PLACEHOLDER.
        }
    }
}
