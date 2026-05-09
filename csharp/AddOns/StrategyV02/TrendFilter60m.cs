namespace AlgoTrading.StrategyV02
{
    public sealed class TrendFilter60m
    {
        public double Ema50 { get; }
        public double Ema200 { get; }
        public double Close { get; }

        public TrendFilter60m(double ema50, double ema200, double close)
        {
            Ema50 = ema50;
            Ema200 = ema200;
            Close = close;
        }

        public bool LongAligned()  => Ema50 > Ema200 && Close > Ema200;
        public bool ShortAligned() => Ema50 < Ema200 && Close < Ema200;
    }
}
