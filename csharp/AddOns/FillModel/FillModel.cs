using AlgoTrading.Domain;

namespace AlgoTrading.FillModel
{
    public sealed class FillModel
    {
        public ICosts Costs { get; }

        public FillModel(ICosts costs = null)
        {
            // Default to placeholder costs if none supplied — same default as Python.
            Costs = costs ?? new PlaceholderCosts();
        }

        public FillResult FillMarket(OrderIntent intent, Tick tick)
        {
            if (intent.Type != OrderType.Market)
                throw new FillModelError("FillMarket requires OrderType.Market");
            int slip = Slip(intent.Side);
            int px = tick.Price + slip;
            return MakeResult(true, px, tick.TsNs, intent.Qty, new[] { "market" });
        }

        public FillResult FillLimitOnTick(OrderIntent intent, Tick tick)
        {
            if (intent.Type != OrderType.Limit)
                throw new FillModelError("FillLimitOnTick requires OrderType.Limit");
            int limit = intent.Price.Value;
            if (intent.Side == OrderSide.Buy && tick.Price <= limit)
                return MakeResult(true, limit, tick.TsNs, intent.Qty, new[] { "limit" });
            if (intent.Side == OrderSide.Sell && tick.Price >= limit)
                return MakeResult(true, limit, tick.TsNs, intent.Qty, new[] { "limit" });
            return null;
        }

        public bool StopTriggered(OrderIntent intent, Tick tick, BBOQuote quote = null)
        {
            if (intent.Type != OrderType.Stop)
                throw new FillModelError("StopTriggered requires OrderType.Stop");
            int stop = intent.Price.Value;
            if (intent.Side == OrderSide.Buy)
            {
                if (tick.Price >= stop) return true;
                if (quote != null && quote.AskPx >= stop) return true;
                return false;
            }
            // SELL stop: covers a long.
            if (tick.Price <= stop) return true;
            if (quote != null && quote.BidPx <= stop) return true;
            return false;
        }

        public FillResult FillStopOnTick(OrderIntent intent, Tick tick, BBOQuote quote = null)
        {
            if (!StopTriggered(intent, tick, quote)) return null;
            int slip = Slip(intent.Side);
            int px = tick.Price + slip;
            return MakeResult(true, px, tick.TsNs, intent.Qty, new[] { "stop_triggered" });
        }

        public FillResult ResolveBracketOnBar(OrderSide side, int qty, int stopLoss, int takeProfit, Bar bar)
        {
            bool hitTarget =
                (side == OrderSide.Buy && bar.High >= takeProfit) ||
                (side == OrderSide.Sell && bar.Low <= takeProfit);
            bool hitStop =
                (side == OrderSide.Buy && bar.Low <= stopLoss) ||
                (side == OrderSide.Sell && bar.High >= stopLoss);

            if (hitTarget && hitStop)
            {
                var res = MakeResult(true, stopLoss, bar.CloseNs, qty, new[] { "bracket", "ambiguous_collision" });
                res.AmbiguousCollision = true;
                return res;
            }
            if (hitTarget)
                return MakeResult(true, takeProfit, bar.CloseNs, qty, new[] { "bracket_target" });
            if (hitStop)
                return MakeResult(true, stopLoss, bar.CloseNs, qty, new[] { "bracket_stop" });
            return new FillResult(false, null, null, 0, 0, new[] { "bracket_pending" });
        }

        private int Slip(OrderSide side)
        {
            if (Costs == null) return 0;
            return side == OrderSide.Buy ? Costs.SlippageTicks : -Costs.SlippageTicks;
        }

        private FillResult MakeResult(bool filled, int? fillPrice, long? fillTsNs,
                                       int qty, string[] notes)
        {
            int cost = Costs?.CommissionPerSideTicks ?? 0;
            string tag = Costs?.Tag ?? "";
            return new FillResult(filled, fillPrice, fillTsNs, qty, cost, notes, tag);
        }
    }
}
