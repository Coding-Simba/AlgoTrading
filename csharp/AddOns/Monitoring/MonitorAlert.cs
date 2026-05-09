namespace AlgoTrading.Monitoring
{
    public sealed class MonitorAlert
    {
        public string Name { get; }
        public long TsNs { get; }
        public string Detail { get; }
        public string Severity { get; }

        public MonitorAlert(string name, long tsNs, string detail, string severity = "warn")
        {
            Name = name;
            TsNs = tsNs;
            Detail = detail;
            Severity = severity;
        }
    }
}
