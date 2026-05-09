using System;
using System.Collections.Generic;
using System.Linq;

namespace AlgoTrading.Monitoring
{
    public sealed class LatencyMonitor
    {
        public string Name { get; }
        public int Window { get; }
        public long WarnNs { get; }
        public long CriticalNs { get; }
        public Queue<long> Samples { get; }
        public List<MonitorAlert> Alerts { get; }

        public LatencyMonitor(string name, int window = 10_000,
                              long warnNs = 50_000_000, long criticalNs = 250_000_000)
        {
            Name = name;
            Window = window;
            WarnNs = warnNs;
            CriticalNs = criticalNs;
            Samples = new Queue<long>();
            Alerts = new List<MonitorAlert>();
        }

        public long Observe(long exchangeNs, long localNs)
        {
            long latency = localNs - exchangeNs;
            if (latency < 0)
                Alerts.Add(new MonitorAlert(Name, localNs, "negative latency " + latency, "critical"));
            Samples.Enqueue(latency);
            while (Samples.Count > Window) Samples.Dequeue();
            if (latency >= CriticalNs)
                Alerts.Add(new MonitorAlert(Name, localNs, "latency " + latency + "ns", "critical"));
            else if (latency >= WarnNs)
                Alerts.Add(new MonitorAlert(Name, localNs, "latency " + latency + "ns", "warn"));
            return latency;
        }

        public long? Percentile(double p)
        {
            if (Samples.Count == 0) return null;
            if (!(p > 0.0 && p < 1.0))
                throw new ArgumentException("p must be in (0, 1)");
            var sorted = Samples.OrderBy(x => x).ToList();
            int idx = Math.Min(sorted.Count - 1, Math.Max(0, (int)Math.Round(p * (sorted.Count - 1))));
            return sorted[idx];
        }
    }
}
