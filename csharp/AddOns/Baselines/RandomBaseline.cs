using System;
using System.Collections.Generic;
using AlgoTrading.Domain;

namespace AlgoTrading.Baselines
{
    public sealed class RandomBaseline : IBaselineRunner
    {
        public int Seed { get; }
        public double PLong { get; }
        public double PShort { get; }
        public string Name { get; }

        public RandomBaseline(int seed = 0, double pLong = 1.0 / 3, double pShort = 1.0 / 3,
                               string name = "random")
        {
            if (pLong < 0 || pShort < 0 || pLong + pShort > 1)
                throw new ArgumentException("invalid probabilities for RandomBaseline");
            Seed = seed;
            PLong = pLong;
            PShort = pShort;
            Name = name;
        }

        public IEnumerable<int> Run(IEnumerable<Bar> bars)
        {
            var rng = new Random(Seed);
            foreach (var _ in bars)
            {
                double r = rng.NextDouble();
                if (r < PLong) yield return SignalValue.Long;
                else if (r < PLong + PShort) yield return SignalValue.Short;
                else yield return SignalValue.Flat;
            }
        }
    }
}
