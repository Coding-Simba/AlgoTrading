using System;
using System.Collections.Generic;

namespace AlgoTrading.Orders
{
    public sealed class ExecutionStateError : Exception
    {
        public ExecutionStateError(string message) : base(message) { }
    }

    public enum ExecutionState
    {
        Flat,
        SignalPending,
        EntrySent,
        EntryFilled,
        BracketPending,
        PositionProtected,
        ExitPending,
        FlatReconciling,
        ErrorHalted
    }

    public sealed class ExecutionHistoryEntry
    {
        public long TsNs { get; }
        public ExecutionState Target { get; }
        public string Reason { get; }
        public ExecutionHistoryEntry(long tsNs, ExecutionState target, string reason)
        {
            TsNs = tsNs;
            Target = target;
            Reason = reason ?? "";
        }
    }

    public sealed class ExecutionLifecycle
    {
        public ExecutionState State { get; private set; } = ExecutionState.Flat;
        public List<ExecutionHistoryEntry> History { get; } = new List<ExecutionHistoryEntry>();

        private static readonly Dictionary<ExecutionState, HashSet<ExecutionState>> Allowed =
            new Dictionary<ExecutionState, HashSet<ExecutionState>>
            {
                { ExecutionState.Flat,              new HashSet<ExecutionState> { ExecutionState.SignalPending } },
                { ExecutionState.SignalPending,     new HashSet<ExecutionState> { ExecutionState.EntrySent, ExecutionState.Flat } },
                { ExecutionState.EntrySent,         new HashSet<ExecutionState> { ExecutionState.EntryFilled, ExecutionState.Flat } },
                { ExecutionState.EntryFilled,       new HashSet<ExecutionState> { ExecutionState.BracketPending } },
                { ExecutionState.BracketPending,    new HashSet<ExecutionState> { ExecutionState.PositionProtected, ExecutionState.ExitPending } },
                { ExecutionState.PositionProtected, new HashSet<ExecutionState> { ExecutionState.ExitPending } },
                { ExecutionState.ExitPending,       new HashSet<ExecutionState> { ExecutionState.FlatReconciling } },
                { ExecutionState.FlatReconciling,   new HashSet<ExecutionState> { ExecutionState.Flat } },
                { ExecutionState.ErrorHalted,       new HashSet<ExecutionState> { ExecutionState.Flat } }
            };

        private static readonly HashSet<ExecutionState> EntryForbiddenOutsideFlat =
            new HashSet<ExecutionState>
            {
                ExecutionState.SignalPending,
                ExecutionState.EntrySent,
                ExecutionState.EntryFilled,
                ExecutionState.BracketPending,
                ExecutionState.PositionProtected,
                ExecutionState.ExitPending,
                ExecutionState.FlatReconciling,
                ExecutionState.ErrorHalted
            };

        public bool CanEmitEntry() => State == ExecutionState.Flat;

        public void Transition(long tsNs, ExecutionState target, string reason = "")
        {
            reason = reason ?? "";

            if (State == ExecutionState.ErrorHalted && target == ExecutionState.Flat)
            {
                if (reason.ToLowerInvariant().IndexOf("manual_review", StringComparison.Ordinal) < 0)
                    throw new ExecutionStateError(
                        "ERROR_HALTED -> FLAT requires manual review (reason must include 'manual_review')");
                Record(tsNs, target, reason);
                return;
            }

            if (target == ExecutionState.SignalPending && EntryForbiddenOutsideFlat.Contains(State))
                throw new ExecutionStateError(
                    "new entry rejected: SignalPending only allowed from Flat, current state is " + State);

            if (!Allowed[State].Contains(target))
                throw new ExecutionStateError(
                    "invalid execution transition " + State + " -> " + target +
                    " (reason: " + (string.IsNullOrEmpty(reason) ? "none" : reason) + ")");

            Record(tsNs, target, reason);
        }

        public void TransitionToError(long tsNs, string reason)
        {
            if (string.IsNullOrWhiteSpace(reason))
                throw new ExecutionStateError("ERROR_HALTED requires a non-empty reason");
            if (State == ExecutionState.ErrorHalted)
                throw new ExecutionStateError("already in ERROR_HALTED");
            Record(tsNs, ExecutionState.ErrorHalted, reason);
        }

        private void Record(long tsNs, ExecutionState target, string reason)
        {
            State = target;
            History.Add(new ExecutionHistoryEntry(tsNs, target, reason));
        }
    }
}
