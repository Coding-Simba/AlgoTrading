using System;
using System.Collections.Generic;

namespace AlgoTrading.Indicators
{
    public static class EMA
    {
        public static double Seed(IReadOnlyList<double> values, int period)
        {
            if (period <= 0) throw new ArgumentException("period must be positive, got " + period);
            if (values.Count < period)
                throw new ArgumentException("need at least " + period + " values to seed EMA, got " + values.Count);
            double sum = 0;
            for (int i = 0; i < period; i++) sum += values[i];
            return sum / period;
        }

        public static List<double?> Compute(IReadOnlyList<double> values, int period)
        {
            if (period <= 0) throw new ArgumentException("period must be positive, got " + period);
            var n = values.Count;
            var outList = new List<double?>(n);
            for (int i = 0; i < n; i++) outList.Add(null);
            if (n < period) return outList;

            double alpha = 2.0 / (period + 1);
            double seed = Seed(values, period);
            outList[period - 1] = seed;
            double prev = seed;
            for (int i = period; i < n; i++)
            {
                prev = alpha * values[i] + (1 - alpha) * prev;
                outList[i] = prev;
            }
            return outList;
        }
    }
}
