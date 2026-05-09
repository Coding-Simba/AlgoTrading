using System.Collections.Generic;

namespace AlgoTrading.Registry
{
    public sealed class RegistryEntry
    {
        public string EntryId { get; }
        public string RegisteredAt { get; }      // ISO-8601 with offset
        public string StrategyVersion { get; }
        public string Family { get; }
        public string RulesHash { get; }
        public IReadOnlyDictionary<string, object> Rules { get; }
        public string RegisteredBy { get; }
        public string Note { get; }
        public string Supersedes { get; }

        public RegistryEntry(string entryId, string registeredAt, string strategyVersion,
                              string family, string rulesHash,
                              IReadOnlyDictionary<string, object> rules,
                              string registeredBy, string note = "",
                              string supersedes = null)
        {
            EntryId = entryId;
            RegisteredAt = registeredAt;
            StrategyVersion = strategyVersion;
            Family = family;
            RulesHash = rulesHash;
            Rules = rules;
            RegisteredBy = registeredBy;
            Note = note ?? "";
            Supersedes = supersedes;
        }
    }
}
