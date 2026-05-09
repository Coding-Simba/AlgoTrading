using System;

namespace AlgoTrading.Domain
{
    public sealed class BBOQuote : IEquatable<BBOQuote>
    {
        public long TsNs { get; }
        public string Symbol { get; }
        public int BidPx { get; }
        public int BidSz { get; }
        public int AskPx { get; }
        public int AskSz { get; }

        public BBOQuote(long tsNs, string symbol, int bidPx, int bidSz, int askPx, int askSz)
        {
            if (tsNs < 0) throw new IngestionException("negative ts_ns: " + tsNs);
            if (bidSz < 0 || askSz < 0) throw new IngestionException("negative size in BBO");
            if (bidPx > askPx && (bidSz != 0 || askSz != 0))
                throw new IngestionException(
                    "crossed book with non-zero sizes: bid " + bidPx + "/" + bidSz +
                    " ask " + askPx + "/" + askSz);

            TsNs = tsNs;
            Symbol = symbol;
            BidPx = bidPx;
            BidSz = bidSz;
            AskPx = askPx;
            AskSz = askSz;
        }

        public bool Equals(BBOQuote other)
        {
            if (other is null) return false;
            return TsNs == other.TsNs && Symbol == other.Symbol
                   && BidPx == other.BidPx && BidSz == other.BidSz
                   && AskPx == other.AskPx && AskSz == other.AskSz;
        }

        public override bool Equals(object obj) => Equals(obj as BBOQuote);

        public override int GetHashCode()
        {
            unchecked
            {
                int h = 17;
                h = h * 31 + TsNs.GetHashCode();
                h = h * 31 + (Symbol?.GetHashCode() ?? 0);
                h = h * 31 + BidPx;
                h = h * 31 + BidSz;
                h = h * 31 + AskPx;
                h = h * 31 + AskSz;
                return h;
            }
        }
    }
}
