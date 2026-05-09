using System.Collections.Generic;
using AlgoTrading.Domain;

namespace AlgoTrading.Baselines
{
    public interface IBaselineRunner
    {
        string Name { get; }
        IEnumerable<int> Run(IEnumerable<Bar> bars);
    }
}
