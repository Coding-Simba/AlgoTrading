namespace AlgoTrading.Governance
{
    public static class PhaseGates
    {
        public static void AssertPreCodeSigned(SignoffMatrix matrix)
        {
            try { matrix.RequireSigned(Gate.V02Code); }
            catch (SignoffError exc) { throw new GateBlocked("pre-code sign-off incomplete: " + exc.Message, exc); }
        }

        public static void AssertApprovedBacktestUnblocked(
            SignoffMatrix matrix,
            RiskLimits riskLimits,
            bool placeholderCostsPresent,
            bool riskLimitsSignedRequired = true)
        {
            AssertPreCodeSigned(matrix);
            var rateSheet = matrix.Find("broker_rate_sheet");
            if (rateSheet == null || !rateSheet.Signed)
                throw new GateBlocked(
                    "approved backtest blocked: broker_rate_sheet row in sign-off matrix is not signed (errata §5)");
            if (placeholderCostsPresent)
                throw new GateBlocked(
                    "approved backtest blocked: fill stream still carries D2_PLACEHOLDER costs (errata §5)");
            if (riskLimitsSignedRequired && (riskLimits == null || !riskLimits.IsSigned()))
                throw new GateBlocked("approved backtest blocked: risk limits are not signed");
        }

        public static void AssertHoldbackUnblocked(
            bool partitionLockSigned,
            bool oosPassRecorded,
            bool holdbackTradeCountThresholdMet)
        {
            if (!partitionLockSigned)
                throw new GateBlocked("holdback blocked: partition lock is not signed");
            if (!oosPassRecorded)
                throw new GateBlocked("holdback blocked: OOS pass for the family is not recorded");
            if (!holdbackTradeCountThresholdMet)
                throw new GateBlocked(
                    "holdback blocked: holdback-partition trade-count floor not met " +
                    "(see docs/data/partition_plan.md §7: 300 family / 150 per side)");
        }

        public static void AssertPaperUnblocked(SignoffMatrix matrix)
        {
            var f = matrix.Find("F");
            if (f == null || !f.Signed)
                throw new GateBlocked(
                    "paper trading blocked: Appendix F (broker integration & OCO finalization) is not signed for the chosen broker");
        }

        public static void AssertLiveUnblocked(
            SignoffMatrix matrix,
            bool brokerOcoConfirmed,
            bool brokerCostsInserted,
            bool appendixFRunbookComplete,
            bool accountControlsConfigured,
            bool maxOrderSizeOneMes,
            bool explicitLiveEnableFlag)
        {
            var paper = matrix.Find("paper");
            if (paper == null || !paper.Signed)
                throw new GateBlocked("live blocked: paper-gate row is not signed");
            if (!brokerOcoConfirmed)
                throw new GateBlocked("live blocked: broker OCO confirmation missing");
            if (!brokerCostsInserted)
                throw new GateBlocked("live blocked: broker costs not yet inserted (errata §5)");
            if (!appendixFRunbookComplete)
                throw new GateBlocked("live blocked: Appendix F broker-specific runbook incomplete");
            if (!accountControlsConfigured)
                throw new GateBlocked("live blocked: account controls not configured");
            if (!maxOrderSizeOneMes)
                throw new GateBlocked("live blocked: max order size must be 1 MES at small-size live");
            if (!explicitLiveEnableFlag)
                throw new GateBlocked(
                    "live blocked: explicit live-enable flag missing (live adapter refuses by default)");
            var smallSize = matrix.Find("small_size_live");
            if (smallSize == null)
                throw new GateBlocked("live blocked: small_size_live row absent from sign-off matrix");
        }

        public static void AssertScaleupUnblocked(SignoffMatrix matrix)
        {
            var g = matrix.Find("G");
            if (g == null || !g.Signed)
                throw new GateBlocked("scale-up blocked: Appendix G is not signed");
            var smallSize = matrix.Find("small_size_live");
            if (smallSize == null || !smallSize.Signed)
                throw new GateBlocked("scale-up blocked: small-size live row is not signed");
        }
    }
}
