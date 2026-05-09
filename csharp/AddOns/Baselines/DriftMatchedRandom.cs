using System;
using System.Collections.Generic;
using AlgoTrading.Domain;

namespace AlgoTrading.Baselines
{
    public sealed class DriftMatchedRandom : IBaselineRunner
    {
        public double DriftPerBar { get; }
        public int Seed { get; }
        public string Name { get; }

        public DriftMatchedRandom(double driftPerBar, int seed = 0, string name = "drift_matched_random")
        {
            DriftPerBar = driftPerBar;
            Seed = seed;
            Name = name;
        }

        public IEnumerable<int> Run(IEnumerable<Bar> bars)
        {
            var rng = new Random(Seed);
            double bias = 0.5 + Math.Max(Math.Min(DriftPerBar * 50.0, 0.4), -0.4);
            foreach (var _ in bars)
                yield return rng.NextDouble() < bias ? SignalValue.Long : SignalValue.Short;
        }
    }
}
