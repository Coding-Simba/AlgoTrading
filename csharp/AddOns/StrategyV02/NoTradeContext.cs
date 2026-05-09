using System;

namespace AlgoTrading.StrategyV02
{
    public sealed class NoTradeContext
    {
        public TimeSpan EtTime { get; set; }
        public bool InNewsBlackout { get; set; }
        public bool InPreNewsFlattenWindow { get; set; }
        public int SpreadTicks { get; set; }
        public double SecondsSinceLastTick { get; set; }
        public bool BboPresent { get; set; } = true;
        public bool BookLockedOrCrossed { get; set; }
        public bool BrokerDegraded { get; set; }
        public bool ExchangeHalt { get; set; }
        public bool LimitUpDown { get; set; }
        public double ClockDriftMs { get; set; }
        public double SignalCalcLatencyS { get; set; }
        public double SignalToOrderLatencyS { get; set; }
        public string OsmState { get; set; } = "FLAT";
        public bool KillSwitchActive { get; set; }
    }
}
