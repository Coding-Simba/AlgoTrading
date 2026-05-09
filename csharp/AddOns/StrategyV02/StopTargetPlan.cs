using AlgoTrading.Domain;

namespace AlgoTrading.StrategyV02
{
    public sealed class StopTargetPlan
    {
        public EntrySide Side { get; }
        public int ExpectedEntry { get; }
        public int CandidateStop { get; }
        public int CandidateR { get; }
        public int? ActualR { get; }
        public int? Target { get; }
        public string SkipReason { get; }

        public StopTargetPlan(EntrySide side, int expectedEntry, int candidateStop, int candidateR,
                              int? actualR, int? target, string skipReason)
        {
            Side = side;
            ExpectedEntry = expectedEntry;
            CandidateStop = candidateStop;
            CandidateR = candidateR;
            ActualR = actualR;
            Target = target;
            SkipReason = skipReason;
        }
    }
}
