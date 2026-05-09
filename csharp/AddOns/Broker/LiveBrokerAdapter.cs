using System.Collections.Generic;
using AlgoTrading.Governance;

namespace AlgoTrading.Broker
{
    /// <summary>
    /// Live broker adapter — safety stub.
    /// Refuses every public method unless every condition listed in
    /// PhaseGates.AssertLiveUnblocked is satisfied. There is no real order
    /// placement code path under v0.2.
    /// </summary>
    public class LiveBrokerAdapter : IBrokerAdapter
    {
        protected SignoffMatrix Matrix { get; }
        public bool BrokerOcoConfirmed { get; set; }
        public bool BrokerCostsInserted { get; set; }
        public bool AppendixFRunbookComplete { get; set; }
        public bool AccountControlsConfigured { get; set; }
        public bool MaxOrderSizeOneMes { get; set; } = true;
        public bool ExplicitLiveEnableFlag { get; set; }

        public LiveBrokerAdapter(SignoffMatrix matrix)
        {
            Matrix = matrix;
        }

        protected void Gate()
        {
            try
            {
                PhaseGates.AssertLiveUnblocked(
                    Matrix,
                    BrokerOcoConfirmed,
                    BrokerCostsInserted,
                    AppendixFRunbookComplete,
                    AccountControlsConfigured,
                    MaxOrderSizeOneMes,
                    ExplicitLiveEnableFlag);
            }
            catch (GateBlocked exc)
            {
                throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: " + exc.Message);
            }
        }

        public virtual string Submit(BrokerOrder order)
        {
            Gate();
            throw new BlockedLiveTrading(
                "BLOCKED_LIVE_TRADING: live order placement is not implemented in v0.2; " +
                "this adapter is a safety stub. Use the paper simulator for synthetic runs.");
        }

        public virtual bool Cancel(string orderId)
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: live cancel not implemented");
        }

        public virtual int CancelAll()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: live cancel_all not implemented");
        }

        public virtual IDictionary<string, int> Positions()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: live positions not implemented");
        }

        public virtual IList<BrokerOrder> WorkingOrders()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: live working_orders not implemented");
        }

        public virtual IList<BrokerFill> Fills()
        {
            Gate();
            throw new BlockedLiveTrading("BLOCKED_LIVE_TRADING: live fills not implemented");
        }
    }
}
