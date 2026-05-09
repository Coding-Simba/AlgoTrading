using System;

namespace AlgoTrading.Registry
{
    public sealed class RegistryError : Exception
    {
        public RegistryError(string message) : base(message) { }
    }
}
