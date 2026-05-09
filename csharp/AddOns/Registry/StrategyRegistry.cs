using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace AlgoTrading.Registry
{
    /// <summary>
    /// Append-only registry, JSONL on disk. Each line is a complete
    /// RegistryEntry record. Lines are never edited or deleted in place.
    /// Mirrors registry.py — same hash function (sha256 over canonical JSON
    /// of `rules`), same id derivation (first 16 hex chars of sha256
    /// of "ts|strategy_version|rules_hash").
    /// </summary>
    public sealed class StrategyRegistry
    {
        public string Path { get; }
        private List<RegistryEntry> _cache = new List<RegistryEntry>();
        private bool _loaded;

        public StrategyRegistry(string path)
        {
            Path = path;
            var dir = System.IO.Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                Directory.CreateDirectory(dir);
            if (!File.Exists(path)) File.WriteAllText(path, "");
        }

        private void Load()
        {
            if (_loaded) return;
            _cache.Clear();
            if (File.Exists(Path))
            {
                foreach (var raw in File.ReadAllLines(Path))
                {
                    var line = raw.Trim();
                    if (string.IsNullOrEmpty(line)) continue;
                    _cache.Add(EntryFromJsonl(line));
                }
            }
            _loaded = true;
        }

        public IReadOnlyList<RegistryEntry> Entries() { Load(); return _cache.AsReadOnly(); }

        public RegistryEntry FindById(string entryId)
        {
            foreach (var e in Entries()) if (e.EntryId == entryId) return e;
            return null;
        }

        public RegistryEntry LatestForVersion(string strategyVersion)
        {
            RegistryEntry latest = null;
            foreach (var e in Entries())
            {
                if (e.StrategyVersion != strategyVersion) continue;
                if (latest == null ||
                    string.Compare(e.RegisteredAt, latest.RegisteredAt, StringComparison.Ordinal) >= 0)
                    latest = e;
            }
            return latest;
        }

        public RegistryEntry Append(string strategyVersion, string family,
                                    IReadOnlyDictionary<string, object> rules,
                                    string registeredBy, string note = "",
                                    string supersedes = null,
                                    string registeredAt = null)
        {
            if (string.IsNullOrEmpty(strategyVersion)) throw new RegistryError("strategy_version is required");
            if (string.IsNullOrEmpty(family))          throw new RegistryError("family is required");
            if (string.IsNullOrEmpty(registeredBy))    throw new RegistryError("registered_by is required");
            if (rules == null || rules.Count == 0)     throw new RegistryError("rules must be non-empty");

            if (supersedes != null && FindById(supersedes) == null)
                throw new RegistryError("supersedes references unknown entry_id: " + supersedes);

            string rulesHash = HashRules(rules);
            string ts = registeredAt ?? DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:sszzz");
            string ident = Sha256Hex(ts + "|" + strategyVersion + "|" + rulesHash).Substring(0, 16);

            var entry = new RegistryEntry(ident, ts, strategyVersion, family,
                                           rulesHash, rules, registeredBy, note, supersedes);

            File.AppendAllText(Path, EntryToJsonl(entry) + "\n");
            _loaded = false;
            return entry;
        }

        public List<string> Validate()
        {
            var errors = new List<string>();
            var seen = new HashSet<string>();
            int lineNo = 0;
            foreach (var e in Entries())
            {
                lineNo++;
                if (!seen.Add(e.EntryId))
                    errors.Add("line " + lineNo + ": duplicate entry_id " + e.EntryId);
                if (HashRules(e.Rules) != e.RulesHash)
                    errors.Add("line " + lineNo + ": rules_hash mismatch for " + e.EntryId);
                if (!string.IsNullOrEmpty(e.Supersedes) && !seen.Contains(e.Supersedes))
                    errors.Add("line " + lineNo + ": supersedes " + e.Supersedes + " not seen earlier");
            }
            return errors;
        }

        // -- minimal JSON support (canonical, sorted keys, integer/string/bool) ---

        private static string HashRules(IReadOnlyDictionary<string, object> rules)
            => Sha256Hex(CanonicalJson(rules));

        private static string Sha256Hex(string s)
        {
            using (var sha = SHA256.Create())
            {
                var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(s));
                var sb = new StringBuilder(bytes.Length * 2);
                foreach (var b in bytes) sb.Append(b.ToString("x2"));
                return sb.ToString();
            }
        }

        private static string CanonicalJson(object value)
        {
            var sb = new StringBuilder();
            EmitJson(sb, value);
            return sb.ToString();
        }

        private static void EmitJson(StringBuilder sb, object v)
        {
            if (v == null) { sb.Append("null"); return; }
            if (v is string s) { sb.Append('"').Append(EscapeJson(s)).Append('"'); return; }
            if (v is bool b)   { sb.Append(b ? "true" : "false"); return; }
            if (v is int i)    { sb.Append(i.ToString(CultureInfo.InvariantCulture)); return; }
            if (v is long l)   { sb.Append(l.ToString(CultureInfo.InvariantCulture)); return; }
            if (v is double d) { sb.Append(d.ToString("R", CultureInfo.InvariantCulture)); return; }
            if (v is IReadOnlyDictionary<string, object> ord)
            {
                sb.Append('{');
                bool first = true;
                foreach (var k in ord.Keys.OrderBy(x => x, StringComparer.Ordinal))
                {
                    if (!first) sb.Append(',');
                    first = false;
                    sb.Append('"').Append(EscapeJson(k)).Append('"').Append(':');
                    EmitJson(sb, ord[k]);
                }
                sb.Append('}');
                return;
            }
            if (v is IDictionary<string, object> idict)
            {
                sb.Append('{');
                bool first = true;
                foreach (var k in idict.Keys.OrderBy(x => x, StringComparer.Ordinal))
                {
                    if (!first) sb.Append(',');
                    first = false;
                    sb.Append('"').Append(EscapeJson(k)).Append('"').Append(':');
                    EmitJson(sb, idict[k]);
                }
                sb.Append('}');
                return;
            }
            if (v is System.Collections.IEnumerable en)
            {
                sb.Append('[');
                bool first = true;
                foreach (var x in en) { if (!first) sb.Append(','); first = false; EmitJson(sb, x); }
                sb.Append(']');
                return;
            }
            sb.Append('"').Append(EscapeJson(v.ToString())).Append('"');
        }

        private static string EscapeJson(string s)
        {
            var sb = new StringBuilder(s.Length);
            foreach (var c in s)
            {
                switch (c)
                {
                    case '"':  sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n");  break;
                    case '\r': sb.Append("\\r");  break;
                    case '\t': sb.Append("\\t");  break;
                    default:
                        if (c < 0x20) sb.AppendFormat("\\u{0:x4}", (int)c);
                        else sb.Append(c);
                        break;
                }
            }
            return sb.ToString();
        }

        private static string EntryToJsonl(RegistryEntry e)
        {
            var dict = new SortedDictionary<string, object>(StringComparer.Ordinal)
            {
                { "entry_id", e.EntryId },
                { "registered_at", e.RegisteredAt },
                { "strategy_version", e.StrategyVersion },
                { "family", e.Family },
                { "rules_hash", e.RulesHash },
                { "rules", e.Rules },
                { "registered_by", e.RegisteredBy },
                { "note", e.Note },
                { "supersedes", (object)e.Supersedes }
            };
            return CanonicalJson((IReadOnlyDictionary<string, object>)dict);
        }

        // Minimal JSONL parser: deserialise our own canonical output (we only
        // produce flat string/int/bool maps). Robust enough for parity with
        // registry.py written by us; not a general-purpose parser.
        private static RegistryEntry EntryFromJsonl(string json)
        {
            var dict = ParseFlatObject(json);
            object rulesObj;
            dict.TryGetValue("rules", out rulesObj);
            var rules = rulesObj as IReadOnlyDictionary<string, object>
                        ?? new Dictionary<string, object>();
            return new RegistryEntry(
                (string)dict["entry_id"],
                (string)dict["registered_at"],
                (string)dict["strategy_version"],
                (string)dict["family"],
                (string)dict["rules_hash"],
                rules,
                (string)dict["registered_by"],
                (string)(dict.ContainsKey("note") ? dict["note"] : ""),
                dict.ContainsKey("supersedes") ? (string)dict["supersedes"] : null);
        }

        private static IReadOnlyDictionary<string, object> ParseFlatObject(string json)
        {
            // Tiny JSON parser sufficient for the canonical output we produce.
            int idx = 0;
            return (IReadOnlyDictionary<string, object>)ParseValue(json, ref idx);
        }

        private static object ParseValue(string s, ref int i)
        {
            SkipWs(s, ref i);
            if (i >= s.Length) throw new RegistryError("unexpected end of JSON");
            char c = s[i];
            if (c == '"') return ParseString(s, ref i);
            if (c == '{') return ParseObject(s, ref i);
            if (c == '[') return ParseArray(s, ref i);
            if (c == 't' || c == 'f') return ParseBool(s, ref i);
            if (c == 'n') { i += 4; return null; }
            return ParseNumber(s, ref i);
        }

        private static void SkipWs(string s, ref int i) { while (i < s.Length && char.IsWhiteSpace(s[i])) i++; }

        private static string ParseString(string s, ref int i)
        {
            if (s[i] != '"') throw new RegistryError("expected '\"' at " + i);
            i++;
            var sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"') return sb.ToString();
                if (c == '\\')
                {
                    char e = s[i++];
                    switch (e)
                    {
                        case '"':  sb.Append('"');  break;
                        case '\\': sb.Append('\\'); break;
                        case 'n':  sb.Append('\n'); break;
                        case 'r':  sb.Append('\r'); break;
                        case 't':  sb.Append('\t'); break;
                        case 'u':
                            int code = int.Parse(s.Substring(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
                            i += 4;
                            sb.Append((char)code);
                            break;
                        default: sb.Append(e); break;
                    }
                }
                else sb.Append(c);
            }
            throw new RegistryError("unterminated string");
        }

        private static IReadOnlyDictionary<string, object> ParseObject(string s, ref int i)
        {
            if (s[i] != '{') throw new RegistryError("expected '{' at " + i);
            i++;
            var dict = new Dictionary<string, object>();
            SkipWs(s, ref i);
            if (i < s.Length && s[i] == '}') { i++; return dict; }
            while (i < s.Length)
            {
                SkipWs(s, ref i);
                string key = ParseString(s, ref i);
                SkipWs(s, ref i);
                if (s[i] != ':') throw new RegistryError("expected ':' at " + i);
                i++;
                object val = ParseValue(s, ref i);
                dict[key] = val;
                SkipWs(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return dict; }
                throw new RegistryError("expected ',' or '}' at " + i);
            }
            throw new RegistryError("unterminated object");
        }

        private static List<object> ParseArray(string s, ref int i)
        {
            if (s[i] != '[') throw new RegistryError("expected '[' at " + i);
            i++;
            var arr = new List<object>();
            SkipWs(s, ref i);
            if (i < s.Length && s[i] == ']') { i++; return arr; }
            while (i < s.Length)
            {
                arr.Add(ParseValue(s, ref i));
                SkipWs(s, ref i);
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return arr; }
                throw new RegistryError("expected ',' or ']' at " + i);
            }
            throw new RegistryError("unterminated array");
        }

        private static bool ParseBool(string s, ref int i)
        {
            if (s[i] == 't') { i += 4; return true; }
            if (s[i] == 'f') { i += 5; return false; }
            throw new RegistryError("expected bool at " + i);
        }

        private static object ParseNumber(string s, ref int i)
        {
            int start = i;
            if (s[i] == '-') i++;
            bool isFloat = false;
            while (i < s.Length && (char.IsDigit(s[i]) || s[i] == '.' || s[i] == 'e' || s[i] == 'E' || s[i] == '+' || s[i] == '-'))
            {
                if (s[i] == '.' || s[i] == 'e' || s[i] == 'E') isFloat = true;
                i++;
            }
            string token = s.Substring(start, i - start);
            if (isFloat) return double.Parse(token, NumberStyles.Float, CultureInfo.InvariantCulture);
            if (long.TryParse(token, NumberStyles.Integer, CultureInfo.InvariantCulture, out var l))
            {
                if (l >= int.MinValue && l <= int.MaxValue) return (int)l;
                return l;
            }
            return double.Parse(token, NumberStyles.Float, CultureInfo.InvariantCulture);
        }
    }
}
