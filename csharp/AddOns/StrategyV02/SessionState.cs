namespace AlgoTrading.StrategyV02
{
    public sealed class SessionState
    {
        public string SessionDate { get; set; }   // "YYYY-MM-DD"
        public SessionCounters Counters { get; set; }
        public bool ErrorHalted { get; set; }

        public SessionState(string sessionDate)
        {
            SessionDate = sessionDate;
            Counters = new SessionCounters();
            ErrorHalted = false;
        }
    }
}
