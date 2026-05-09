using System;

namespace AlgoTrading.Domain
{
    public sealed class Tick : IEquatable<Tick>
    {
        public long TsNs { get; }
        public string Symbol { get; }
        public int Price { get; }
        public int Size { get; }
        public string Aggressor { get; }

        public Tick(long tsNs, string symbol, int price, int size, string aggressor)
        {
            if (tsNs < 0) throw new IngestionException("negative ts_ns: " + tsNs);
            if (size <= 0) throw new IngestionException("non-positive size: " + size);
            if (aggressor != "B" && aggressor != "S" && aggressor != "U")
                throw new IngestionException("invalid aggressor: " + (aggressor ?? "null"));

            TsNs = tsNs;
            Symbol = symbol;
            Price = price;
            Size = size;
            Aggressor = aggressor;
        }

        public bool Equals(Tick other)
        {
            if (other is null) return false;
            return TsNs == other.TsNs
                   && Symbol == other.Symbol
                   && Price == other.Price
                   && Size == other.Size
                   && Aggressor == other.Aggressor;
        }

        public override bool Equals(object obj) => Equals(obj as Tick);

        public override int GetHashCode()
        {
            unchecked
            {
                int h = 17;
                h = h * 31 + TsNs.GetHashCode();
                h = h * 31 + (Symbol?.GetHashCode() ?? 0);
                h = h * 31 + Price;
                h = h * 31 + Size;
                h = h * 31 + (Aggressor?.GetHashCode() ?? 0);
                return h;
            }
        }
    }
}
