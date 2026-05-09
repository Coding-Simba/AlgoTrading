namespace AlgoTrading.FillModel
{
    public interface ICosts
    {
        int CommissionPerSideTicks { get; }
        int SlippageTicks { get; }
        string Tag { get; }
    }
}
