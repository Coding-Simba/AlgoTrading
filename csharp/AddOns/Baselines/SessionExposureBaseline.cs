using System.Collections.Generic;
using AlgoTrading.Domain;
using AlgoTrading.Calendar;

namespace AlgoTrading.Baselines
{
    public sealed class SessionExposureBaseline : IBaselineRunner
    {
        public SessionCalendar Calendar { get; }
        public string Name { get; }

        public SessionExposureBaseline(SessionCalendar calendar, string name = "session_exposure")
        {
            Calendar = calendar;
            Name = name;
        }

        public IEnumerable<int> Run(IEnumerable<Bar> bars)
        {
            foreach (var bar in bars)
                yield return Calendar.IsOpen(bar.OpenNs) ? SignalValue.Long : SignalValue.Flat;
        }
    }
}
