using System;

namespace AlgoTrading.FillModel
{
    public sealed class FillModelError : Exception
    {
        public FillModelError(string message) : base(message) { }
    }
}
