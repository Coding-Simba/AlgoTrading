namespace AlgoTrading.Broker
{
    public sealed class BrokerOrder
    {
        public string ClientOrderId { get; }
        public string Symbol { get; }
        public string Side { get; }      // "buy" | "sell"
        public int Qty { get; }
        public string OrderType { get; } // "market" | "limit" | "stop"
        public int? Price { get; }       // price in ticks; null for market
        public string ParentId { get; }  // null when no parent

        public BrokerOrder(string clientOrderId, string symbol, string side,
                           int qty, string orderType, int? price,
                           string parentId = null)
        {
            ClientOrderId = clientOrderId;
            Symbol = symbol;
            Side = side;
            Qty = qty;
            OrderType = orderType;
            Price = price;
            ParentId = parentId;
        }
    }
}
