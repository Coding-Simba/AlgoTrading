using System;
using System.Collections.Generic;
using System.Linq;

namespace AlgoTrading.Orders
{
    public sealed class FlattenSequenceError : Exception
    {
        public FlattenSequenceError(string message) : base(message) { }
    }

    public enum FlattenStep
    {
        HaltNewEntries,
        KeepStopActive,
        SubmitMarketFlatten,
        ConfirmBrokerFlat,
        CancelRemainingOco,
        AtomicFlatten
    }

    public static class FlattenSequence
    {
        public static readonly IReadOnlyList<FlattenStep> Default = new[]
        {
            FlattenStep.HaltNewEntries,
            FlattenStep.KeepStopActive,
            FlattenStep.SubmitMarketFlatten,
            FlattenStep.ConfirmBrokerFlat,
            FlattenStep.CancelRemainingOco
        };

        public static readonly IReadOnlyList<FlattenStep> Atomic = new[]
        {
            FlattenStep.HaltNewEntries,
            FlattenStep.AtomicFlatten,
            FlattenStep.ConfirmBrokerFlat
        };

        public static IReadOnlyList<FlattenStep> ProtectedFlattenPlan(
            bool atomicFlatten = false,
            bool brokerAtomicFlattenDocumented = false)
        {
            if (atomicFlatten)
            {
                if (!brokerAtomicFlattenDocumented)
                    throw new FlattenSequenceError(
                        "atomicFlatten requires brokerAtomicFlattenDocumented=true; the documented " +
                        "broker/OCO confirmation must record a broker-native atomic flatten path. " +
                        "Default sequence (cancel-after-flatten) is the only sanctioned alternative.");
                return Atomic;
            }
            return Default;
        }

        public static void ValidateFlattenPlan(IReadOnlyList<FlattenStep> plan, bool atomicFlatten = false)
        {
            if (plan == null || plan.Count == 0)
                throw new FlattenSequenceError("flatten plan must not be empty");
            if (!plan.Contains(FlattenStep.HaltNewEntries))
                throw new FlattenSequenceError("plan missing HaltNewEntries");
            if (!plan.Contains(FlattenStep.ConfirmBrokerFlat))
                throw new FlattenSequenceError("plan missing ConfirmBrokerFlat");
            if (plan[0] != FlattenStep.HaltNewEntries)
                throw new FlattenSequenceError("HaltNewEntries must be the first step");

            if (atomicFlatten)
            {
                if (!plan.Contains(FlattenStep.AtomicFlatten))
                    throw new FlattenSequenceError("atomicFlatten=true but plan does not include AtomicFlatten");
                if (plan.Contains(FlattenStep.CancelRemainingOco))
                    throw new FlattenSequenceError(
                        "atomic flatten plan must not include CancelRemainingOco; " +
                        "the broker-native atomic call owns the cancel");
                if (plan.Contains(FlattenStep.SubmitMarketFlatten))
                    throw new FlattenSequenceError(
                        "atomic flatten plan must not include SubmitMarketFlatten; " +
                        "atomic call replaces the manual flatten");
                return;
            }

            if (!plan.Contains(FlattenStep.KeepStopActive))
                throw new FlattenSequenceError(
                    "default plan must include KeepStopActive; cancel-first is rejected unless atomicFlatten=true");
            if (!plan.Contains(FlattenStep.SubmitMarketFlatten))
                throw new FlattenSequenceError("default plan must include SubmitMarketFlatten");

            int keepIdx    = plan.ToList().IndexOf(FlattenStep.KeepStopActive);
            int flattenIdx = plan.ToList().IndexOf(FlattenStep.SubmitMarketFlatten);
            int confirmIdx = plan.ToList().IndexOf(FlattenStep.ConfirmBrokerFlat);

            if (!(keepIdx < flattenIdx))
                throw new FlattenSequenceError("KeepStopActive must precede SubmitMarketFlatten");
            if (!(flattenIdx < confirmIdx))
                throw new FlattenSequenceError("SubmitMarketFlatten must precede ConfirmBrokerFlat");

            int cancelIdx = plan.ToList().IndexOf(FlattenStep.CancelRemainingOco);
            if (cancelIdx >= 0 && !(confirmIdx < cancelIdx))
                throw new FlattenSequenceError(
                    "CancelRemainingOco must come AFTER ConfirmBrokerFlat — " +
                    "cancel-before-flatten is forbidden unless atomicFlatten=true");
        }
    }
}
