using System;
using System.Globalization;

namespace AlgoTrading.Contamination
{
    public sealed class LogRow
    {
        public static readonly string[] AllowedActions = {
            "parameter_change", "rule_change", "variant_tested",
            "validation_query", "data_qa_check", "other"
        };
        public static readonly string[] AllowedDatasets = {
            "training", "validation", "live", "paper", "none"
        };
        public static readonly string[] AllowedDecisions = {
            "kept", "discarded", "logged_for_next_version", "escalated"
        };

        public string DatetimeIso { get; }
        public string Researcher { get; }
        public string StrategyVersion { get; }
        public string ActionType { get; }
        public string Description { get; }
        public string DatasetUsed { get; }
        public string ResultObserved { get; }
        public string Decision { get; }
        public string ReviewerInitials { get; }
        public string ReviewerDate { get; }

        public LogRow(string datetimeIso, string researcher, string strategyVersion,
                      string actionType, string description, string datasetUsed,
                      string resultObserved, string decision,
                      string reviewerInitials = "", string reviewerDate = "")
        {
            DatetimeIso = datetimeIso ?? "";
            Researcher = researcher ?? "";
            StrategyVersion = strategyVersion ?? "";
            ActionType = actionType ?? "";
            Description = description ?? "";
            DatasetUsed = datasetUsed ?? "";
            ResultObserved = resultObserved ?? "";
            Decision = decision ?? "";
            ReviewerInitials = reviewerInitials ?? "";
            ReviewerDate = reviewerDate ?? "";
        }

        public void Validate()
        {
            if (Array.IndexOf(AllowedActions, ActionType) < 0)
                throw new ContaminationError("action_type '" + ActionType + "' not allowed");
            if (Array.IndexOf(AllowedDatasets, DatasetUsed) < 0)
                throw new ContaminationError("dataset_used '" + DatasetUsed + "' not allowed");
            if (Array.IndexOf(AllowedDecisions, Decision) < 0)
                throw new ContaminationError("decision '" + Decision + "' not allowed");
            if (string.IsNullOrEmpty(Researcher))
                throw new ContaminationError("researcher is required");
            if (string.IsNullOrEmpty(StrategyVersion))
                throw new ContaminationError("strategy_version is required");
            if (!DateTimeOffset.TryParse(DatetimeIso, CultureInfo.InvariantCulture,
                    DateTimeStyles.AssumeUniversal, out _))
                throw new ContaminationError("datetime_iso not ISO-8601: " + DatetimeIso);
        }

        public string[] ToFields() => new[]
        {
            DatetimeIso, Researcher, StrategyVersion, ActionType, Description,
            DatasetUsed, ResultObserved, Decision, ReviewerInitials, ReviewerDate
        };
    }
}
