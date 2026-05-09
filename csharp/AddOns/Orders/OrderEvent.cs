namespace AlgoTrading.Orders
{
    public enum OrderEvent
    {
        Submit,
        Ack,
        Reject,
        PartialFill,
        Fill,
        Cancel,
        Expire
    }
}
