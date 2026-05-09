using System.Collections.Generic;

namespace AlgoTrading.Orders
{
    public sealed class OrderStateMachine
    {
        public OrderRecord Record { get; }

        private static readonly HashSet<OrderState> Terminal = new HashSet<OrderState>
        {
            OrderState.Filled,
            OrderState.Canceled,
            OrderState.Rejected,
            OrderState.Expired
        };

        private static readonly Dictionary<OrderState, HashSet<OrderState>> Allowed =
            new Dictionary<OrderState, HashSet<OrderState>>
            {
                { OrderState.New,         new HashSet<OrderState> { OrderState.PendingNew, OrderState.Rejected } },
                { OrderState.PendingNew,  new HashSet<OrderState> { OrderState.Working, OrderState.Rejected } },
                { OrderState.Working,     new HashSet<OrderState> { OrderState.PartialFill, OrderState.Filled,
                                                                    OrderState.Canceled, OrderState.Expired } },
                { OrderState.PartialFill, new HashSet<OrderState> { OrderState.PartialFill, OrderState.Filled,
                                                                    OrderState.Canceled, OrderState.Expired } },
                { OrderState.Filled,      new HashSet<OrderState>() },
                { OrderState.Canceled,    new HashSet<OrderState>() },
                { OrderState.Rejected,    new HashSet<OrderState>() },
                { OrderState.Expired,     new HashSet<OrderState>() }
            };

        public OrderStateMachine(OrderRecord record)
        {
            Record = record;
        }

        public void Submit(long tsNs)  => Transition(tsNs, OrderEvent.Submit, OrderState.PendingNew);
        public void Ack(long tsNs)     => Transition(tsNs, OrderEvent.Ack,    OrderState.Working);
        public void Reject(long tsNs)  => Transition(tsNs, OrderEvent.Reject, OrderState.Rejected);
        public void Cancel(long tsNs)  => Transition(tsNs, OrderEvent.Cancel, OrderState.Canceled);
        public void Expire(long tsNs)  => Transition(tsNs, OrderEvent.Expire, OrderState.Expired);

        public void Fill(long tsNs, int qty)
        {
            if (qty <= 0)
                throw new OrderStateError("fill qty must be positive, got " + qty);
            if (qty > Record.Remaining())
                throw new OrderStateError("fill qty " + qty + " exceeds remaining " + Record.Remaining());

            Record.QtyFilled += qty;
            if (Record.QtyFilled == Record.QtyTotal)
                Transition(tsNs, OrderEvent.Fill, OrderState.Filled);
            else
                Transition(tsNs, OrderEvent.PartialFill, OrderState.PartialFill);
        }

        private void Transition(long tsNs, OrderEvent ev, OrderState target)
        {
            var cur = Record.State;
            if (Terminal.Contains(cur))
                throw new OrderStateError("cannot " + ev + " from terminal state " + cur);
            if (!Allowed[cur].Contains(target))
                throw new OrderStateError("invalid transition " + cur + " -> " + target + " on " + ev);
            Record.State = target;
            Record.History.Add(new OrderHistoryEntry(tsNs, ev, target));
        }
    }
}
