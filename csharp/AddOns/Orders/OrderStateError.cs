using System;

namespace AlgoTrading.Orders
{
    public sealed class OrderStateError : Exception
    {
        public OrderStateError(string message) : base(message) { }
    }
}
