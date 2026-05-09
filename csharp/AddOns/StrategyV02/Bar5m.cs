namespace AlgoTrading.StrategyV02
{
    public sealed class Bar5m
    {
        public int High { get; }
        public int Low { get; }
        public int Close { get; }

        public Bar5m(int high, int low, int close)
        {
            High = high;
            Low = low;
            Close = close;
        }
    }
}
