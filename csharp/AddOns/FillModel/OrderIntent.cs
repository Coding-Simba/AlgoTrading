namespace AlgoTrading.FillModel
{
    public sealed class OrderIntent
    {
        public OrderSide Side { get; }
        public int Qty { get; }
        public OrderType Type { get; }
        public int? Price { get; }
        public int? StopLoss { get; }
        public int? TakeProfit { get; }

        public OrderIntent(OrderSide side, int qty, OrderType type,
                           int? price = null, int? stopLoss = null, int? takeProfit = null)
        {
            if (qty <= 0) throw new FillModelError("qty must be positive, got " + qty);
            if ((type == OrderType.Limit || type == OrderType.Stop) && !price.HasValue)
                throw new FillModelError("price required for " + type);

            Side = side;
            Qty = qty;
            Type = type;
            Price = price;
            StopLoss = stopLoss;
            TakeProfit = takeProfit;
        }
    }
}
