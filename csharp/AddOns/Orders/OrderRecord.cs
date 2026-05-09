using System.Collections.Generic;

namespace AlgoTrading.Orders
{
    public sealed class OrderRecord
    {
        public string OrderId { get; }
        public OrderState State { get; internal set; }
        public int QtyTotal { get; }
        public int QtyFilled { get; internal set; }
        public List<OrderHistoryEntry> History { get; }

        public OrderRecord(string orderId, int qtyTotal,
                           OrderState state = OrderState.New,
                           int qtyFilled = 0)
        {
            OrderId = orderId;
            State = state;
            QtyTotal = qtyTotal;
            QtyFilled = qtyFilled;
            History = new List<OrderHistoryEntry>();
        }

        public int Remaining() => QtyTotal - QtyFilled;

        public bool IsTerminal()
        {
            return State == OrderState.Filled
                || State == OrderState.Canceled
                || State == OrderState.Rejected
                || State == OrderState.Expired;
        }
    }

    public sealed class OrderHistoryEntry
    {
        public long TsNs { get; }
        public OrderEvent Event { get; }
        public OrderState Target { get; }

        public OrderHistoryEntry(long tsNs, OrderEvent ev, OrderState target)
        {
            TsNs = tsNs;
            Event = ev;
            Target = target;
        }
    }
}
