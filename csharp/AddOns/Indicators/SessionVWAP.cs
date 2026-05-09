using System;
using System.Collections.Generic;
using System.Linq;

namespace AlgoTrading.Indicators
{
    public static class SessionVWAP
    {
        public static List<double?> Compute(
            IReadOnlyList<double> prices,
            IReadOnlyList<double> volumes,
            IReadOnlyList<int> sessionStartIndices)
        {
            int n = prices.Count;
            if (n != volumes.Count)
                throw new ArgumentException("prices and volumes must be same length");

            var starts = sessionStartIndices.Select(s => (int)s).Distinct().OrderBy(x => x).ToList();
            if (starts.Count > 0 && (starts[0] < 0 || starts[starts.Count - 1] >= n))
                throw new ArgumentException("session_start_indices out of range");

            var outList = new List<double?>(n);
            for (int i = 0; i < n; i++) outList.Add(null);
            if (starts.Count == 0) return outList;

            for (int i = 0; i < starts.Count; i++)
            {
                int start = starts[i];
                int end = (i + 1 < starts.Count) ? starts[i + 1] : n;
                double cumPv = 0;
                double cumV = 0;
                for (int j = start; j < end; j++)
                {
                    cumPv += prices[j] * volumes[j];
                    cumV += volumes[j];
                    outList[j] = cumV > 0 ? (double?)(cumPv / cumV) : null;
                }
            }
            return outList;
        }
    }
}
