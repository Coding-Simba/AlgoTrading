namespace AlgoTrading.Orders
{
    public enum OrderState
    {
        New,
        PendingNew,
        Working,
        PartialFill,
        Filled,
        Canceled,
        Rejected,
        Expired
    }
}
