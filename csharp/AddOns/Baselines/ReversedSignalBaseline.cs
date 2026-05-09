using System.Collections.Generic;
using AlgoTrading.Domain;

namespace AlgoTrading.Baselines
{
    public sealed class ReversedSignalBaseline : IBaselineRunner
    {
        public IBaselineRunner Inner { get; }
        public string Name { get; }

        public ReversedSignalBaseline(IBaselineRunner inner, string name = "reversed_signal")
        {
            Inner = inner;
            Name = name;
        }

        public IEnumerable<int> Run(IEnumerable<Bar> bars)
        {
            foreach (var s in Inner.Run(bars))
                yield return -s;
        }
    }
}
