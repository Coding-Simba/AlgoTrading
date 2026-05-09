using AlgoTrading.Governance;

namespace AlgoTrading.Backtest
{
    /// <summary>
    /// Wrappers around AlgoTrading.Governance.PhaseGates with the specific
    /// entry-points the backtest engine, training runner, OOS runner, and
    /// holdback runner each call. Mirrors backtest/gates.py.
    /// </summary>
    public static class BacktestGates
    {
        public static void EnforceSyntheticOnly(string label = "synthetic") { /* noop */ }

        public static void EnforcePreCode(SignoffMatrix matrix)
            => PhaseGates.AssertPreCodeSigned(matrix);

        public static void EnforceApprovedBacktest(SignoffMatrix matrix, RiskLimits riskLimits,
                                                    bool placeholderCostsPresent)
            => PhaseGates.AssertApprovedBacktestUnblocked(matrix, riskLimits, placeholderCostsPresent);

        public static void EnforceHoldback(bool partitionLockSigned, bool oosPassRecorded,
                                            bool holdbackTradeCountThresholdMet)
            => PhaseGates.AssertHoldbackUnblocked(
                partitionLockSigned, oosPassRecorded, holdbackTradeCountThresholdMet);
    }
}
