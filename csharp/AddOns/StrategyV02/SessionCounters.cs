namespace AlgoTrading.StrategyV02
{
    public sealed class SessionCounters
    {
        public int TradesEnteredToday { get; set; }
        public int OpenPositions { get; set; }

        public bool CanEnter() => TradesEnteredToday < 3 && OpenPositions == 0;

        public void OnEntry()
        {
            TradesEnteredToday += 1;
            OpenPositions += 1;
        }

        public void OnExit()
        {
            if (OpenPositions > 0) OpenPositions -= 1;
        }
    }
}
