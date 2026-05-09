using System.Collections.Generic;
using AlgoTrading.Domain;

namespace AlgoTrading.Bars
{
    public sealed class BarBuilder
    {
        public long IntervalNs { get; }
        public long AnchorNs { get; }

        private long? _openNs;
        private int? _open;
        private int? _high;
        private int? _low;
        private int? _close;
        private long _volume;
        private int _count;

        public BarBuilder(long intervalNs, long anchorNs = 0)
        {
            if (intervalNs <= 0)
                throw new BarBuilderError("intervalNs must be positive, got " + intervalNs);
            IntervalNs = intervalNs;
            AnchorNs = anchorNs;
        }

        private long Floor(long tsNs)
        {
            long delta = tsNs - AnchorNs;
            return AnchorNs + (delta / IntervalNs) * IntervalNs;
        }

        public Bar Push(Tick tick)
        {
            long barOpen = Floor(tick.TsNs);

            if (_openNs == null)
            {
                Begin(barOpen, tick);
                return null;
            }

            if (barOpen == _openNs.Value)
            {
                Extend(tick);
                return null;
            }

            if (barOpen < _openNs.Value)
                throw new BarBuilderError(
                    "non-monotonic tick: ts_ns=" + tick.TsNs + " floors to " + barOpen +
                    " but current bar opens at " + _openNs.Value);

            Bar completed = Snapshot();
            Begin(barOpen, tick);
            return completed;
        }

        public Bar Flush()
        {
            if (_openNs == null) return null;
            Bar b = Snapshot();
            _openNs = null;
            _open = _high = _low = _close = null;
            _volume = 0;
            _count = 0;
            return b;
        }

        private void Begin(long barOpen, Tick tick)
        {
            _openNs = barOpen;
            _open = _high = _low = _close = tick.Price;
            _volume = tick.Size;
            _count = 1;
        }

        private void Extend(Tick tick)
        {
            if (tick.Price > _high.Value) _high = tick.Price;
            if (tick.Price < _low.Value)  _low = tick.Price;
            _close = tick.Price;
            _volume += tick.Size;
            _count += 1;
        }

        private Bar Snapshot()
        {
            return new Bar(
                openNs: _openNs.Value,
                closeNs: _openNs.Value + IntervalNs,
                open: _open.Value,
                high: _high.Value,
                low: _low.Value,
                close: _close.Value,
                volume: _volume,
                tickCount: _count,
                intervalNs: IntervalNs);
        }

        public static IEnumerable<Bar> BuildBars(IEnumerable<Tick> ticks, long intervalNs, long anchorNs = 0)
        {
            var b = new BarBuilder(intervalNs, anchorNs);
            foreach (var t in ticks)
            {
                var bar = b.Push(t);
                if (bar != null) yield return bar;
            }
            var final = b.Flush();
            if (final != null) yield return final;
        }
    }
}
