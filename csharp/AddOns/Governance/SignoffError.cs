using System;

namespace AlgoTrading.Governance
{
    public sealed class SignoffError : Exception
    {
        public SignoffError(string message) : base(message) { }
    }
}
