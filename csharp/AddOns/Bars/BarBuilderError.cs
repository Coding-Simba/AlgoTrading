using System;

namespace AlgoTrading.Bars
{
    public sealed class BarBuilderError : Exception
    {
        public BarBuilderError(string message) : base(message) { }
    }
}
