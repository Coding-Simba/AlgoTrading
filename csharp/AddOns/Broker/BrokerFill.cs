namespace AlgoTrading.Broker
{
    public sealed class BrokerFill
    {
        public string OrderId { get; }
        public string Symbol { get; }
        public string Side { get; }
        public int Qty { get; }
        public int Price { get; }    // ticks
        public long TsNs { get; }
        public string CostTag { get; }

        public BrokerFill(string orderId, string symbol, string side, int qty,
                          int price, long tsNs, string costTag = "")
        {
            OrderId = orderId;
            Symbol = symbol;
            Side = side;
            Qty = qty;
            Price = price;
            TsNs = tsNs;
            CostTag = costTag ?? "";
        }
    }
}
