using System;

namespace AlgoTrading.Governance
{
    public class GateBlocked : Exception
    {
        public GateBlocked(string message) : base(message) { }
        public GateBlocked(string message, Exception inner) : base(message, inner) { }
    }
}
