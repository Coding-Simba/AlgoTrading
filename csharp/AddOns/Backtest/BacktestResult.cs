using System.Collections.Generic;

namespace AlgoTrading.Backtest
{
    /// <summary>
    /// Run summary for a synthetic / approved backtest. The Python version
    /// wraps a PaperRunResult; we keep the same fields and let callers
    /// populate them. The PaperSimulator port is deferred — NinjaScript
    /// users will run NT8's own Strategy Analyzer instead.
    /// </summary>
    public sealed class BacktestResult
    {
        public int BarsProcessed { get; set; }
        public int SignalsSeen { get; set; }
        public int EntriesTaken { get; set; }
        public int SkipsDueToAtrFilter { get; set; }
        public int SkipsDueToNoTrade { get; set; }
        public int Fills { get; set; }
        public int ErrorHaltedCount { get; set; }
        public int PlaceholderCostFills { get; set; }
        public List<string> Notes { get; set; } = new List<string>();
        public bool Approved { get; set; } = false;

        public bool PlaceholderCostTagPresent => PlaceholderCostFills > 0;

        public void StampApproved()
        {
            if (PlaceholderCostTagPresent)
                throw new System.InvalidOperationException(
                    "approved backtest blocked: D2_PLACEHOLDER present in result");
            Approved = true;
        }
    }
}
