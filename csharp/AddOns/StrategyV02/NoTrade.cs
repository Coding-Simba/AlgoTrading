using System;
using System.Collections.Generic;

namespace AlgoTrading.StrategyV02
{
    public static class NoTrade
    {
        // ET signal window per Appendix B §B.8: 10:35 ET to 15:30 ET (inclusive).
        private static readonly TimeSpan SignalWindowOpen  = new TimeSpan(10, 35, 0);
        private static readonly TimeSpan SignalWindowClose = new TimeSpan(15, 30, 0);

        private static bool OutsideSignalWindow(TimeSpan t)
            => t < SignalWindowOpen || t > SignalWindowClose;

        public static List<NoTradeReason> BlockingReasons(NoTradeContext ctx)
        {
            var outList = new List<NoTradeReason>();
            if (OutsideSignalWindow(ctx.EtTime))         outList.Add(NoTradeReason.OutsideSignalWindow);
            if (ctx.InNewsBlackout)                      outList.Add(NoTradeReason.NewsBlackout);
            if (ctx.InPreNewsFlattenWindow)              outList.Add(NoTradeReason.PreNewsFlatten);
            if (ctx.SpreadTicks > 2)                     outList.Add(NoTradeReason.SpreadTooWide);
            if (ctx.SecondsSinceLastTick > 3)            outList.Add(NoTradeReason.StaleTick);
            if (!ctx.BboPresent)                         outList.Add(NoTradeReason.MissingBbo);
            if (ctx.BookLockedOrCrossed)                 outList.Add(NoTradeReason.LockedOrCrossedBook);
            if (ctx.BrokerDegraded)                      outList.Add(NoTradeReason.BrokerDegraded);
            if (ctx.ExchangeHalt)                        outList.Add(NoTradeReason.ExchangeHalt);
            if (ctx.LimitUpDown)                         outList.Add(NoTradeReason.LimitUpDown);
            if (ctx.ClockDriftMs > 250)                  outList.Add(NoTradeReason.ClockDriftOver250Ms);
            if (ctx.SignalCalcLatencyS > 2)              outList.Add(NoTradeReason.SignalLatencyOver2S);
            if (ctx.SignalToOrderLatencyS > 3)           outList.Add(NoTradeReason.OrderLatencyOver3S);
            if (!string.Equals(ctx.OsmState, "FLAT", StringComparison.OrdinalIgnoreCase))
                outList.Add(NoTradeReason.OsmNotFlat);
            if (ctx.KillSwitchActive)                    outList.Add(NoTradeReason.KillSwitchActive);
            return outList;
        }
    }
}
