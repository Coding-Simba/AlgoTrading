using System.Collections.Generic;

namespace AlgoTrading.Governance
{
    public sealed class RiskLimits
    {
        public double? AllocatedCapitalUsd { get; }
        public double? MaxOosDrawdownPct { get; }
        public int? MaxAcceptableLosingStreak { get; }
        public double? DailyLossLimitUsd { get; }
        public double? AggregateProgramDrawdownLimitPct { get; }
        public double? RiskOfRuinThresholdPct { get; }
        public string SignedBy { get; }
        public string SignedAtIso { get; }
        public bool Locked { get; }

        public RiskLimits(double? allocatedCapitalUsd, double? maxOosDrawdownPct,
                          int? maxAcceptableLosingStreak, double? dailyLossLimitUsd,
                          double? aggregateProgramDrawdownLimitPct, double? riskOfRuinThresholdPct,
                          string signedBy, string signedAtIso, bool locked)
        {
            AllocatedCapitalUsd = allocatedCapitalUsd;
            MaxOosDrawdownPct = maxOosDrawdownPct;
            MaxAcceptableLosingStreak = maxAcceptableLosingStreak;
            DailyLossLimitUsd = dailyLossLimitUsd;
            AggregateProgramDrawdownLimitPct = aggregateProgramDrawdownLimitPct;
            RiskOfRuinThresholdPct = riskOfRuinThresholdPct;
            SignedBy = signedBy ?? "";
            SignedAtIso = signedAtIso ?? "";
            Locked = locked;
        }

        public List<string> ValidationErrors()
        {
            var errors = new List<string>();
            if (!Locked) errors.Add("locked is false");
            if (string.IsNullOrWhiteSpace(SignedBy)) errors.Add("signed_by is empty");
            if (!SignoffMatrix.IsIso8601(SignedAtIso)) errors.Add("signed_at_iso is not ISO-8601");

            if (!AllocatedCapitalUsd.HasValue) errors.Add("allocated_capital_usd is missing");
            else if (AllocatedCapitalUsd.Value <= 0) errors.Add("allocated_capital_usd must be > 0");

            if (!MaxOosDrawdownPct.HasValue) errors.Add("max_oos_drawdown_pct is missing");
            else if (!(MaxOosDrawdownPct.Value > 0 && MaxOosDrawdownPct.Value < 100))
                errors.Add("max_oos_drawdown_pct must be in (0, 100)");

            if (!MaxAcceptableLosingStreak.HasValue) errors.Add("max_acceptable_losing_streak is missing");
            else if (MaxAcceptableLosingStreak.Value < 1) errors.Add("max_acceptable_losing_streak must be >= 1");

            if (!DailyLossLimitUsd.HasValue) errors.Add("daily_loss_limit_usd is missing");
            else if (DailyLossLimitUsd.Value <= 0) errors.Add("daily_loss_limit_usd must be > 0");

            if (!AggregateProgramDrawdownLimitPct.HasValue) errors.Add("aggregate_program_drawdown_limit_pct is missing");
            else if (!(AggregateProgramDrawdownLimitPct.Value > 0 && AggregateProgramDrawdownLimitPct.Value < 100))
                errors.Add("aggregate_program_drawdown_limit_pct must be in (0, 100)");

            if (!RiskOfRuinThresholdPct.HasValue) errors.Add("risk_of_ruin_threshold_pct is missing");
            else if (!(RiskOfRuinThresholdPct.Value > 0 && RiskOfRuinThresholdPct.Value < 100))
                errors.Add("risk_of_ruin_threshold_pct must be in (0, 100)");

            return errors;
        }

        public bool IsSigned() => ValidationErrors().Count == 0;

        public void AssertSigned()
        {
            var errors = ValidationErrors();
            if (errors.Count > 0)
                throw new RiskLimitsError("risk limits not signed: " + string.Join("; ", errors));
        }
    }
}
