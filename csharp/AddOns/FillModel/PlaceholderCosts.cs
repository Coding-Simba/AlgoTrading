namespace AlgoTrading.FillModel
{
    /// <summary>Placeholder costs per §D.2. NOT for approved backtests (errata §5).</summary>
    public sealed class PlaceholderCosts : ICosts
    {
        public int CommissionPerSideTicks { get; }
        public int SlippageTicks { get; }
        public string Tag { get; }

        public PlaceholderCosts(int commissionPerSideTicks = 1, int slippageTicks = 1)
        {
            CommissionPerSideTicks = commissionPerSideTicks;
            SlippageTicks = slippageTicks;
            Tag = FillModelConstants.D2PlaceholderTag;
        }
    }
}
