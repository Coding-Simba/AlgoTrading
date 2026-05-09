namespace AlgoTrading.StrategyV02
{
    public enum NoTradeReason
    {
        OutsideSignalWindow,
        NewsBlackout,
        PreNewsFlatten,
        SpreadTooWide,
        StaleTick,
        MissingBbo,
        LockedOrCrossedBook,
        BrokerDegraded,
        ExchangeHalt,
        LimitUpDown,
        ClockDriftOver250Ms,
        SignalLatencyOver2S,
        OrderLatencyOver3S,
        OsmNotFlat,
        KillSwitchActive
    }
}
