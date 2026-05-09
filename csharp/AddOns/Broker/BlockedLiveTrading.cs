using AlgoTrading.Governance;

namespace AlgoTrading.Broker
{
    /// <summary>Specific subclass so callers can grep for `BLOCKED_LIVE_TRADING`.</summary>
    public sealed class BlockedLiveTrading : GateBlocked
    {
        public BlockedLiveTrading(string message) : base(message) { }
    }
}
