using System;

namespace AlgoTrading.Domain
{
    public sealed class IngestionException : Exception
    {
        public IngestionException(string message) : base(message) { }
    }
}
