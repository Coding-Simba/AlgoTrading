using System;
using System.Collections.Generic;
using System.Linq;

namespace AlgoTrading.Calendar
{
    public sealed class SessionCalendar
    {
        private const long NsPerSecond = 1_000_000_000L;

        public string Timezone { get; }
        public IReadOnlyList<SessionWindow> Windows { get; }

        public SessionCalendar(string timezone, IEnumerable<SessionWindow> windows)
        {
            Timezone = timezone;
            var sorted = (windows ?? Enumerable.Empty<SessionWindow>())
                .OrderBy(w => w.OpenNs)
                .ToList();

            SessionWindow prev = null;
            foreach (var w in sorted)
            {
                if (w.SessionType == SessionType.Holiday) continue;
                if (prev != null && prev.SessionType != SessionType.Holiday)
                {
                    if (w.OpenNs < prev.CloseNs)
                        throw new CalendarError("overlapping windows: " + prev.Label + " and " + w.Label);
                }
                prev = w;
            }
            Windows = sorted;
        }

        public bool IsOpen(long tsNs) => WindowFor(tsNs) != null;

        public SessionWindow WindowFor(long tsNs)
        {
            foreach (var w in Windows)
            {
                if (w.SessionType == SessionType.Holiday) continue;
                if (w.Contains(tsNs)) return w;
            }
            return null;
        }

        public long? NextCloseAfter(long tsNs)
        {
            foreach (var w in Windows)
            {
                if (w.SessionType == SessionType.Holiday) continue;
                if (w.CloseNs > tsNs) return w.CloseNs;
            }
            return null;
        }

        public bool IsHoliday(long tsNs)
        {
            DateTime d = DateOf(tsNs);
            foreach (var w in Windows)
            {
                if (w.SessionType == SessionType.Holiday && DateOf(w.OpenNs) == d)
                    return true;
            }
            return false;
        }

        public bool IsHalfDay(long tsNs)
        {
            var w = WindowFor(tsNs);
            return w != null && w.SessionType == SessionType.HalfDay;
        }

        private static DateTime DateOf(long tsNs)
        {
            // UTC date corresponding to ts_ns.
            long seconds = tsNs / NsPerSecond;
            return new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc).AddSeconds(seconds).Date;
        }
    }
}
