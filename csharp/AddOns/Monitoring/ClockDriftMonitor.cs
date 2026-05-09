using System;
using System.Collections.Generic;
using System.Linq;

namespace AlgoTrading.Monitoring
{
    public sealed class ClockDriftMonitor
    {
        public string Name { get; }
        public int Window { get; }
        public long WarnNs { get; }
        public long CriticalNs { get; }
        public Queue<long> Samples { get; }
        public List<MonitorAlert> Alerts { get; }

        public ClockDriftMonitor(string name, int window = 1_000,
                                 long warnNs = 10_000_000,
                                 long criticalNs = 250_000_000)
        {
            Name = name;
            Window = window;
            WarnNs = warnNs;
            CriticalNs = criticalNs;
            Samples = new Queue<long>();
            Alerts = new List<MonitorAlert>();
        }

        public long Observe(long localNs, long referenceNs)
        {
            long drift = localNs - referenceNs;
            Samples.Enqueue(drift);
            while (Samples.Count > Window) Samples.Dequeue();
            long mag = Math.Abs(drift);
            if (mag >= CriticalNs)
                Alerts.Add(new MonitorAlert(Name, localNs, "clock drift " + drift + "ns", "critical"));
            else if (mag >= WarnNs)
                Alerts.Add(new MonitorAlert(Name, localNs, "clock drift " + drift + "ns", "warn"));
            return drift;
        }

        public double? RollingMean()
        {
            if (Samples.Count == 0) return null;
            return Samples.Average();
        }
    }
}
