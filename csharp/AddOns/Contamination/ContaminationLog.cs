using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace AlgoTrading.Contamination
{
    /// <summary>
    /// Append-only research contamination log, RFC-4180 CSV.
    /// Header columns match log.py exactly. Rows are validated on append.
    /// </summary>
    public sealed class ContaminationLog
    {
        public static readonly string[] Header = {
            "datetime_iso", "researcher", "strategy_version", "action_type",
            "description", "dataset_used", "result_observed", "decision",
            "reviewer_initials", "reviewer_date"
        };

        public string Path { get; }

        public ContaminationLog(string path)
        {
            Path = path;
            var dir = System.IO.Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);
            if (!File.Exists(path) || new FileInfo(path).Length == 0)
                File.WriteAllText(path, FormatRow(Header));
        }

        public void Append(LogRow row)
        {
            row.Validate();
            File.AppendAllText(Path, FormatRow(row.ToFields()));
        }

        public List<LogRow> ReadAll()
        {
            if (!File.Exists(Path)) return new List<LogRow>();
            var lines = File.ReadAllLines(Path);
            if (lines.Length == 0) return new List<LogRow>();
            var first = ParseRow(lines[0]);
            if (!first.SequenceEqual(Header))
                throw new ContaminationError("header mismatch: [" + string.Join(", ", first) + "]");
            var rows = new List<LogRow>();
            for (int i = 1; i < lines.Length; i++)
            {
                if (string.IsNullOrEmpty(lines[i])) continue;
                var fields = ParseRow(lines[i]);
                if (fields.Count != Header.Length)
                    throw new ContaminationError("malformed row: [" + string.Join(", ", fields) + "]");
                rows.Add(new LogRow(
                    fields[0], fields[1], fields[2], fields[3], fields[4],
                    fields[5], fields[6], fields[7], fields[8], fields[9]));
            }
            return rows;
        }

        public string NowIso() => DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:sszzz");

        // -- RFC-4180 minimal CSV -------------------------------------------

        private static string FormatRow(IList<string> fields)
        {
            var sb = new StringBuilder();
            for (int i = 0; i < fields.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(QuoteIfNeeded(fields[i] ?? ""));
            }
            sb.Append('\n');
            return sb.ToString();
        }

        private static string QuoteIfNeeded(string s)
        {
            bool needs = s.IndexOfAny(new[] { ',', '"', '\n', '\r' }) >= 0;
            if (!needs) return s;
            return "\"" + s.Replace("\"", "\"\"") + "\"";
        }

        private static List<string> ParseRow(string line)
        {
            var fields = new List<string>();
            var cur = new StringBuilder();
            bool inQuotes = false;
            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (inQuotes)
                {
                    if (c == '"')
                    {
                        if (i + 1 < line.Length && line[i + 1] == '"') { cur.Append('"'); i++; }
                        else inQuotes = false;
                    }
                    else cur.Append(c);
                }
                else
                {
                    if (c == ',') { fields.Add(cur.ToString()); cur.Clear(); }
                    else if (c == '"' && cur.Length == 0) inQuotes = true;
                    else cur.Append(c);
                }
            }
            fields.Add(cur.ToString());
            return fields;
        }
    }
}
