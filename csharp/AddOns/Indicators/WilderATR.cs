using System;
using System.Collections.Generic;

namespace AlgoTrading.Indicators
{
    public static class WilderATR
    {
        public static List<double?> Compute(
            IReadOnlyList<double> highs,
            IReadOnlyList<double> lows,
            IReadOnlyList<double> closes,
            int period = 14)
        {
            if (period <= 0) throw new ArgumentException("period must be positive, got " + period);
            int n = highs.Count;
            if (n != lows.Count || n != closes.Count)
                throw new ArgumentException("highs/lows/closes must be same length");

            var outList = new List<double?>(n);
            for (int i = 0; i < n; i++) outList.Add(null);
            if (n < period + 1) return outList;

            // True ranges TR[i] (size n-1, indexed from 1 to n-1).
            var trs = new List<double>(n - 1);
            for (int i = 1; i < n; i++)
            {
                double tr = Math.Max(
                    highs[i] - lows[i],
                    Math.Max(
                        Math.Abs(highs[i] - closes[i - 1]),
                        Math.Abs(lows[i] - closes[i - 1])));
                trs.Add(tr);
            }

            double seedSum = 0;
            for (int i = 0; i < period; i++) seedSum += trs[i];
            double seed = seedSum / period;
            outList[period] = seed;

            double prev = seed;
            double alpha = 1.0 / period;
            for (int i = period + 1; i < n; i++)
            {
                prev = alpha * trs[i - 1] + (1 - alpha) * prev;
                outList[i] = prev;
            }
            return outList;
        }
    }
}
