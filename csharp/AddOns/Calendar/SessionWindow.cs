namespace AlgoTrading.Calendar
{
    public sealed class SessionWindow
    {
        public long OpenNs { get; }
        public long CloseNs { get; }
        public SessionType SessionType { get; }
        public string Label { get; }

        public SessionWindow(long openNs, long closeNs, SessionType sessionType, string label = "")
        {
            if (sessionType != SessionType.Holiday && closeNs <= openNs)
                throw new CalendarError("CloseNs (" + closeNs + ") must exceed OpenNs (" + openNs + ")");
            OpenNs = openNs;
            CloseNs = closeNs;
            SessionType = sessionType;
            Label = label ?? "";
        }

        public bool Contains(long tsNs) => OpenNs <= tsNs && tsNs < CloseNs;
    }
}
