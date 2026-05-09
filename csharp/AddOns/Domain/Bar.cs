using System;

namespace AlgoTrading.Domain
{
    public sealed class Bar : IEquatable<Bar>
    {
        public long OpenNs { get; }
        public long CloseNs { get; }
        public int Open { get; }
        public int High { get; }
        public int Low { get; }
        public int Close { get; }
        public long Volume { get; }
        public int TickCount { get; }
        public long IntervalNs { get; }

        public Bar(long openNs, long closeNs, int open, int high, int low, int close,
                   long volume, int tickCount, long intervalNs)
        {
            OpenNs = openNs;
            CloseNs = closeNs;
            Open = open;
            High = high;
            Low = low;
            Close = close;
            Volume = volume;
            TickCount = tickCount;
            IntervalNs = intervalNs;
        }

        public bool Equals(Bar other)
        {
            if (other is null) return false;
            return OpenNs == other.OpenNs && CloseNs == other.CloseNs
                   && Open == other.Open && High == other.High
                   && Low == other.Low && Close == other.Close
                   && Volume == other.Volume && TickCount == other.TickCount
                   && IntervalNs == other.IntervalNs;
        }

        public override bool Equals(object obj) => Equals(obj as Bar);

        public override int GetHashCode()
        {
            unchecked
            {
                int h = 17;
                h = h * 31 + OpenNs.GetHashCode();
                h = h * 31 + CloseNs.GetHashCode();
                h = h * 31 + Open;
                h = h * 31 + High;
                h = h * 31 + Low;
                h = h * 31 + Close;
                h = h * 31 + Volume.GetHashCode();
                h = h * 31 + TickCount;
                h = h * 31 + IntervalNs.GetHashCode();
                return h;
            }
        }
    }
}
