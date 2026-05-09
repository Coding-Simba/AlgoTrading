namespace AlgoTrading.Governance
{
    public static class Gate
    {
        public const string V02Code        = "v0.2_code";
        public const string V02Backtest    = "v0.2_backtest";
        public const string Validation     = "validation";
        public const string Paper          = "paper";
        public const string Live           = "live";
        public const string Scaleup        = "scaleup";
        public const string ScopeExpansion = "scope_expansion";

        public static readonly string[] All =
        {
            V02Code, V02Backtest, Validation, Paper, Live, Scaleup, ScopeExpansion
        };
    }
}
