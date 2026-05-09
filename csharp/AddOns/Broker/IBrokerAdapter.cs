using System.Collections.Generic;

namespace AlgoTrading.Broker
{
    public interface IBrokerAdapter
    {
        string Submit(BrokerOrder order);
        bool Cancel(string orderId);
        int CancelAll();
        IDictionary<string, int> Positions();
        IList<BrokerOrder> WorkingOrders();
        IList<BrokerFill> Fills();
    }
}
