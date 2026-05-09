using System;
using System.Collections.Generic;
using AlgoTrading.Domain;

namespace AlgoTrading.StrategyV02
{
    public static class Rules
    {
        // MES tick = 0.25 index points; we work in ticks (integer) end-to-end.
        private const int TickSize = 1;

        public static int RoundToTick(double price, EntrySide side)
        {
            if (side == EntrySide.Long)
                return (int)Math.Floor(price / TickSize) * TickSize;
            return (int)Math.Ceiling(price / TickSize) * TickSize;
        }

        private static int? PullbackLong(IReadOnlyList<Bar5m> bars,
                                          IReadOnlyList<double?> ema20,
                                          IReadOnlyList<double?> vwap)
        {
            if (bars.Count < 3) return null;
            int n = bars.Count;
            bool pullbackSeen = false;

            for (int k = 0; k < 3; k++)
            {
                int idx = n - 3 + k;
                Bar5m b = bars[idx];
                var thresholds = new List<double>(2);
                if (ema20[idx].HasValue) thresholds.Add(ema20[idx].Value);
                if (vwap[idx].HasValue) thresholds.Add(vwap[idx].Value);
                if (thresholds.Count == 0) continue;
                foreach (var t in thresholds)
                {
                    if (b.Low <= t) { pullbackSeen = true; break; }
                }
                if (pullbackSeen) break;
            }
            if (!pullbackSeen) return null;

            int min = bars[n - 3].Low;
            for (int k = n - 2; k <= n - 1; k++)
                if (bars[k].Low < min) min = bars[k].Low;
            return min;
        }

        private static int? PullbackShort(IReadOnlyList<Bar5m> bars,
                                           IReadOnlyList<double?> ema20,
                                           IReadOnlyList<double?> vwap)
        {
            if (bars.Count < 3) return null;
            int n = bars.Count;
            bool pullbackSeen = false;

            for (int k = 0; k < 3; k++)
            {
                int idx = n - 3 + k;
                Bar5m b = bars[idx];
                var thresholds = new List<double>(2);
                if (ema20[idx].HasValue) thresholds.Add(ema20[idx].Value);
                if (vwap[idx].HasValue) thresholds.Add(vwap[idx].Value);
                if (thresholds.Count == 0) continue;
                foreach (var t in thresholds)
                {
                    if (b.High >= t) { pullbackSeen = true; break; }
                }
                if (pullbackSeen) break;
            }
            if (!pullbackSeen) return null;

            int max = bars[n - 3].High;
            for (int k = n - 2; k <= n - 1; k++)
                if (bars[k].High > max) max = bars[k].High;
            return max;
        }

        public static EntrySignal LongSignal(
            IReadOnlyList<Bar5m> bars5m,
            IReadOnlyList<double?> ema200_5m,
            IReadOnlyList<double?> ema20_5m,
            IReadOnlyList<double?> vwap_5m,
            TrendFilter60m trend60m)
        {
            if (bars5m.Count < 4) return null;
            if (!trend60m.LongAligned()) return null;
            var last = bars5m[bars5m.Count - 1];
            var prev = bars5m[bars5m.Count - 2];
            var lastEma200 = ema200_5m[ema200_5m.Count - 1];
            if (!lastEma200.HasValue || last.Close <= lastEma200.Value) return null;
            int? pullbackLow = PullbackLong(bars5m, ema20_5m, vwap_5m);
            if (!pullbackLow.HasValue) return null;
            if (last.Close <= prev.High) return null;
            return new EntrySignal(EntrySide.Long, pullbackLow.Value);
        }

        public static EntrySignal ShortSignal(
            IReadOnlyList<Bar5m> bars5m,
            IReadOnlyList<double?> ema200_5m,
            IReadOnlyList<double?> ema20_5m,
            IReadOnlyList<double?> vwap_5m,
            TrendFilter60m trend60m)
        {
            if (bars5m.Count < 4) return null;
            if (!trend60m.ShortAligned()) return null;
            var last = bars5m[bars5m.Count - 1];
            var prev = bars5m[bars5m.Count - 2];
            var lastEma200 = ema200_5m[ema200_5m.Count - 1];
            if (!lastEma200.HasValue || last.Close >= lastEma200.Value) return null;
            int? pullbackHigh = PullbackShort(bars5m, ema20_5m, vwap_5m);
            if (!pullbackHigh.HasValue) return null;
            if (last.Close >= prev.Low) return null;
            return new EntrySignal(EntrySide.Short, pullbackHigh.Value);
        }

        private static string RPassesAtrFilter(int candidateR, double atr14)
        {
            if (candidateR <= 0) return "candidate_R_non_positive";
            if (candidateR > 1.5 * atr14) return "candidate_R_too_large";
            if (candidateR < 0.5 * atr14) return "candidate_R_too_small";
            return null;
        }

        public static StopTargetPlan PlanLong(int pullbackLow, int currentAsk,
                                               int modeledSlippageTicks, double atr14,
                                               int? actualEntryFill = null)
        {
            int expectedEntry = currentAsk + modeledSlippageTicks;
            int candidateStop = pullbackLow - 1;
            int candidateR = expectedEntry - candidateStop;
            string skip = RPassesAtrFilter(candidateR, atr14);
            if (skip != null || !actualEntryFill.HasValue)
            {
                return new StopTargetPlan(
                    EntrySide.Long, expectedEntry, candidateStop, candidateR,
                    actualR: null, target: null, skipReason: skip);
            }
            int actualR = actualEntryFill.Value - candidateStop;
            if (actualR <= 0)
            {
                return new StopTargetPlan(
                    EntrySide.Long, expectedEntry, candidateStop, candidateR,
                    actualR: actualR, target: null,
                    skipReason: "actual_R_non_positive_error_halted");
            }
            int target = RoundToTick(actualEntryFill.Value + 1.5 * actualR, EntrySide.Long);
            return new StopTargetPlan(
                EntrySide.Long, expectedEntry, candidateStop, candidateR,
                actualR: actualR, target: target, skipReason: null);
        }

        public static StopTargetPlan PlanShort(int pullbackHigh, int currentBid,
                                                int modeledSlippageTicks, double atr14,
                                                int? actualEntryFill = null)
        {
            int expectedEntry = currentBid - modeledSlippageTicks;
            int candidateStop = pullbackHigh + 1;
            int candidateR = candidateStop - expectedEntry;
            string skip = RPassesAtrFilter(candidateR, atr14);
            if (skip != null || !actualEntryFill.HasValue)
            {
                return new StopTargetPlan(
                    EntrySide.Short, expectedEntry, candidateStop, candidateR,
                    actualR: null, target: null, skipReason: skip);
            }
            int actualR = candidateStop - actualEntryFill.Value;
            if (actualR <= 0)
            {
                return new StopTargetPlan(
                    EntrySide.Short, expectedEntry, candidateStop, candidateR,
                    actualR: actualR, target: null,
                    skipReason: "actual_R_non_positive_error_halted");
            }
            int target = RoundToTick(actualEntryFill.Value - 1.5 * actualR, EntrySide.Short);
            return new StopTargetPlan(
                EntrySide.Short, expectedEntry, candidateStop, candidateR,
                actualR: actualR, target: target, skipReason: null);
        }
    }
}
