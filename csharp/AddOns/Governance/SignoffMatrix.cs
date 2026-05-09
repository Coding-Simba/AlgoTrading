using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

namespace AlgoTrading.Governance
{
    public sealed class SignoffMatrix
    {
        public string SourcePath { get; }
        public IReadOnlyList<SignoffRow> Rows { get; }

        public SignoffMatrix(string sourcePath, IEnumerable<SignoffRow> rows)
        {
            SourcePath = sourcePath ?? "";
            var list = (rows ?? Enumerable.Empty<SignoffRow>()).ToList();

            // Reject duplicates (same as the Python loader).
            var seen = new HashSet<string>();
            foreach (var r in list)
            {
                if (!seen.Add(r.Id))
                    throw new SignoffError("duplicate sign-off row id: " + r.Id);
                if (Array.IndexOf(Gate.All, r.RequiredFor) < 0)
                    throw new SignoffError(
                        "sign-off row '" + r.Id + "': required_for '" + r.RequiredFor +
                        "' is not a recognised gate");
            }
            Rows = list;
        }

        public IList<SignoffRow> RowsForGate(string gate)
            => Rows.Where(r => r.RequiredFor == gate).ToList();

        public SignoffRow Find(string rowId)
            => Rows.FirstOrDefault(r => r.Id == rowId);

        public static bool IsIso8601(string value)
        {
            if (string.IsNullOrWhiteSpace(value)) return false;
            return DateTimeOffset.TryParse(
                value,
                CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal,
                out _);
        }

        public static bool RowIsSigned(SignoffRow row)
        {
            if (row == null) return false;
            return row.Signed
                && !string.IsNullOrWhiteSpace(row.SignedBy)
                && IsIso8601(row.SignedAtIso);
        }

        public void RequireSigned(string gate)
        {
            if (Array.IndexOf(Gate.All, gate) < 0)
                throw new SignoffError("unknown gate '" + gate + "'");
            var relevant = RowsForGate(gate);
            if (relevant.Count == 0)
                throw new SignoffError("no sign-off rows declared for gate '" + gate + "'");

            var unsigned = new List<string>();
            var badSigner = new List<string>();
            var badDate = new List<string>();
            foreach (var r in relevant)
            {
                if (!r.Signed) { unsigned.Add(r.Id); continue; }
                if (string.IsNullOrWhiteSpace(r.SignedBy)) { badSigner.Add(r.Id); continue; }
                if (!IsIso8601(r.SignedAtIso)) { badDate.Add(r.Id); continue; }
            }
            var problems = new List<string>();
            if (unsigned.Count > 0)  problems.Add("unsigned rows: [" + string.Join(", ", unsigned.OrderBy(s => s)) + "]");
            if (badSigner.Count > 0) problems.Add("missing signed_by: [" + string.Join(", ", badSigner.OrderBy(s => s)) + "]");
            if (badDate.Count > 0)   problems.Add("unparseable signed_at_iso: [" + string.Join(", ", badDate.OrderBy(s => s)) + "]");
            if (problems.Count > 0)
                throw new SignoffError(
                    "sign-off matrix at " + SourcePath + " blocks gate '" + gate + "': " +
                    string.Join("; ", problems));
        }
    }
}
