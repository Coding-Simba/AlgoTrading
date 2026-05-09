using System.Collections.Generic;

namespace AlgoTrading.FillModel
{
    public sealed class FillResult
    {
        public bool Filled { get; }
        public int? FillPrice { get; }
        public long? FillTsNs { get; }
        public int Qty { get; }
        public int CostTicks { get; }
        public List<string> Notes { get; }
        public bool AmbiguousCollision { get; set; }
        public string CostTag { get; }

        public FillResult(bool filled, int? fillPrice, long? fillTsNs, int qty,
                          int costTicks, IEnumerable<string> notes, string costTag = "")
        {
            Filled = filled;
            FillPrice = fillPrice;
            FillTsNs = fillTsNs;
            Qty = qty;
            CostTicks = costTicks;
            Notes = notes != null ? new List<string>(notes) : new List<string>();
            CostTag = costTag ?? "";
        }

        public bool IsPlaceholder() => CostTag == FillModelConstants.D2PlaceholderTag;
    }
}
