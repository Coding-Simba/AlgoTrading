using System;

namespace AlgoTrading.Contamination
{
    public sealed class ContaminationError : Exception
    {
        public ContaminationError(string message) : base(message) { }
    }
}
