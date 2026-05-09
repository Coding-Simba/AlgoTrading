using System;

namespace AlgoTrading.Calendar
{
    public sealed class CalendarError : Exception
    {
        public CalendarError(string message) : base(message) { }
    }
}
