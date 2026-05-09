using AlgoTrading.Domain;

namespace AlgoTrading.StrategyV02
{
    public sealed class EntrySignal
    {
        public EntrySide Side { get; }
        public int PullbackLowOrHigh { get; }

        public EntrySignal(EntrySide side, int pullbackLowOrHigh)
        {
            Side = side;
            PullbackLowOrHigh = pullbackLowOrHigh;
        }
    }
}
