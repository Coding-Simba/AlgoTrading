using System;

namespace AlgoTrading.Governance
{
    public sealed class RiskLimitsError : Exception
    {
        public RiskLimitsError(string message) : base(message) { }
    }
}
