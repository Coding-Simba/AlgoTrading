"""Tom3 + candidate(s) portfolio combo analyzer.

Reads NT8 trade-export CSVs for Tom3 and each candidate strategy, builds a
common-date daily P&L matrix, then evaluates portfolio combos using the
user's *own* NT8 numbers (not workbook P&L).

Usage:
    python combo_analysis.py \
        --tom3   "...Tom3 trades.csv" \
        --cand   OvernightCounter="...OC trades.csv" \
        --cand   VariableTrend="...VT trades.csv" \
        --out    combo_results.md

Each input CSV must be a NinjaTrader Strategy Analyzer "Trades" export
(the same format as the Tom3 file we already parsed). The script handles
trade-by-trade rows and aggregates by Exit date.
"""

from __future__ import annotations
import argparse
import csv
import sys
from datetime import date, datetime
from itertools import combinations
from pathlib import Path
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")

# -------------------- CSV parsing --------------------

def parse_money(s: str) -> float:
    """NT8 money cells: '$1234.56', '($1234.56)' for negative, '$0.00', blank."""
    if not s:
        return 0.0
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    if not s:
        return 0.0
    return -float(s) if neg else float(s)


def parse_nt8_trades(path: Path) -> dict[date, float]:
    """Read NT8 trade-export CSV → daily realized P&L by Exit date.

    Handles both 12-hour ("5:14:00 PM") and 24-hour ("17:14:00") time formats.
    Net of commission/clearing/exchange/IP/NFA fees if those columns are present.
    """
    daily: dict[date, float] = {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        rd = csv.DictReader(f)
        for row in rd:
            exit_time = (row.get("Exit time") or row.get("ExitTime") or "").strip()
            if not exit_time:
                continue
            dt = None
            for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S",
                        "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
                try:
                    dt = datetime.strptime(exit_time, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                continue
            profit = parse_money(row.get("Profit", ""))
            fees = sum(parse_money(row.get(k, "")) for k in (
                "Commission", "Clearing Fee", "Exchange Fee", "IP Fee", "NFA Fee"
            ))
            net = profit - fees
            d = dt.date()
            daily[d] = daily.get(d, 0.0) + net
    return daily


# -------------------- Metrics --------------------

def drawdown_series(pnl: list[float]) -> list[float]:
    eq, peak = 0.0, 0.0
    dd = []
    for p in pnl:
        eq += p
        peak = max(peak, eq)
        dd.append(eq - peak)
    return dd


def equity_series(pnl: list[float]) -> list[float]:
    out = []
    eq = 0.0
    for p in pnl:
        eq += p
        out.append(eq)
    return out


def metrics(pnl: list[float]) -> dict:
    if not pnl or all(p == 0 for p in pnl):
        return {k: 0 for k in ("net", "pf", "max_dd", "active_days",
                               "win_days", "loss_days", "win_rate",
                               "ret_dd", "worst_day", "best_day",
                               "worst_week", "worst_month", "avg_day")}
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p < 0]
    dd = drawdown_series(pnl)
    active = sum(1 for p in pnl if p != 0)
    # rolling 5-day and 21-day worst
    n = len(pnl)
    worst_week = min((sum(pnl[i:i+5]) for i in range(max(1, n - 4))), default=0)
    worst_month = min((sum(pnl[i:i+21]) for i in range(max(1, n - 20))), default=0)
    return {
        "net": sum(pnl),
        "pf": (sum(wins) / -sum(losses)) if losses and sum(losses) != 0 else 0,
        "max_dd": min(dd),
        "active_days": active,
        "win_days": len(wins),
        "loss_days": len(losses),
        "win_rate": (len(wins) / active) if active else 0,
        "ret_dd": (sum(pnl) / abs(min(dd))) if min(dd) < 0 else 0,
        "worst_day": min(pnl) if pnl else 0,
        "best_day": max(pnl) if pnl else 0,
        "worst_week": worst_week,
        "worst_month": worst_month,
        "avg_day": mean(pnl) if pnl else 0,
    }


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def worst_day_cushion(tom3: list[float], cand: list[float], top_n: int = 20) -> dict:
    """For Tom3's worst N days, what did the candidate do?"""
    paired = sorted(zip(tom3, cand), key=lambda x: x[0])[:top_n]
    return {
        "sum": sum(c for _, c in paired),
        "n_pos": sum(1 for _, c in paired if c > 0),
        "n_neg": sum(1 for _, c in paired if c < 0),
        "avg": mean([c for _, c in paired]) if paired else 0,
    }


def dd_overlap_days(series_list: list[list[float]]) -> int:
    """Days when ALL series are simultaneously below their respective peaks."""
    dds = [drawdown_series(s) for s in series_list]
    n = len(dds[0]) if dds else 0
    return sum(1 for i in range(n) if all(d[i] < -1 for d in dds))


# -------------------- Combo evaluation --------------------

def combine(daily_maps: list[dict[date, float]]) -> tuple[list[date], list[float]]:
    """Merge multiple per-day-PnL dicts into a single sorted date list and summed-PnL list."""
    all_dates = sorted(set().union(*(m.keys() for m in daily_maps)))
    summed = [sum(m.get(d, 0.0) for m in daily_maps) for d in all_dates]
    return all_dates, summed


def align(daily_maps: dict[str, dict[date, float]]) -> tuple[list[date], dict[str, list[float]]]:
    all_dates = sorted(set().union(*(m.keys() for m in daily_maps.values())))
    aligned = {name: [m.get(d, 0.0) for d in all_dates] for name, m in daily_maps.items()}
    return all_dates, aligned


# -------------------- Report --------------------

def fmt_money(v: float) -> str:
    if v == 0:
        return "$0"
    sign = "" if v >= 0 else "-"
    return f"{sign}${abs(v):,.0f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tom3", required=True, help="Path to Tom3 trade-export CSV")
    ap.add_argument("--cand", action="append", default=[],
                    help="Candidate as NAME=path/to/csv. Repeatable.")
    ap.add_argument("--out", default="combo_results.md", help="Output markdown path")
    ap.add_argument("--start", default=None, help="Start date (YYYY-MM-DD) — restricts analysis")
    ap.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")
    args = ap.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d").date() if args.start else None
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None

    def in_range(d: date) -> bool:
        if start_date and d < start_date:
            return False
        if end_date and d > end_date:
            return False
        return True

    print(f"Loading Tom3: {args.tom3}")
    tom3_full = parse_nt8_trades(Path(args.tom3))
    tom3 = {d: v for d, v in tom3_full.items() if in_range(d)}
    print(f"  {len(tom3)} days, net {fmt_money(sum(tom3.values()))}")

    candidates: dict[str, dict[date, float]] = {}
    for spec in args.cand:
        name, _, path = spec.partition("=")
        if not name or not path:
            print(f"  bad --cand spec: {spec!r}, expected NAME=path")
            continue
        full = parse_nt8_trades(Path(path))
        cand = {d: v for d, v in full.items() if in_range(d)}
        candidates[name] = cand
        print(f"  {name}: {len(cand)} days, net {fmt_money(sum(cand.values()))}")

    # Align all strategies on a common date grid
    all_maps = {"Tom3": tom3, **candidates}
    dates, aligned = align(all_maps)

    # Per-strategy metrics
    per_strat = {n: metrics(aligned[n]) for n in aligned}

    # Pairwise correlations
    names = list(aligned.keys())
    corr_matrix = {a: {b: pearson(aligned[a], aligned[b]) for b in names} for a in names}

    # Tom3 worst-day cushion per candidate
    cushion = {n: worst_day_cushion(aligned["Tom3"], aligned[n])
               for n in candidates}

    # Build all non-empty subsets of candidates and evaluate Tom3 + subset
    cand_names = list(candidates.keys())
    combos = []
    for r in range(0, len(cand_names) + 1):
        for combo in combinations(cand_names, r):
            label = "Tom3" if not combo else "Tom3+" + "+".join(combo)
            pnl = [aligned["Tom3"][i] + sum(aligned[c][i] for c in combo)
                   for i in range(len(dates))]
            m = metrics(pnl)
            m["dd_overlap"] = dd_overlap_days([aligned["Tom3"]] + [aligned[c] for c in combo])
            combos.append({"label": label, "members": ("Tom3",) + combo, "m": m})

    # Year-by-year breakdown per strategy
    year_breakdown: dict[str, dict[int, float]] = {}
    for n in names:
        year_breakdown[n] = {}
        for d, v in zip(dates, aligned[n]):
            year_breakdown[n][d.year] = year_breakdown[n].get(d.year, 0.0) + v

    # Write report
    out = Path(args.out)
    with out.open("w", encoding="utf-8") as fp:
        fp.write("# Tom3 + candidate portfolio combo analysis (NT8 own numbers)\n\n")
        fp.write(f"Date range: {dates[0]} .. {dates[-1]} ({len(dates)} days)  \n")
        fp.write(f"Tom3 trades CSV: `{args.tom3}`  \n")
        for n, c in candidates.items():
            fp.write(f"{n} trades CSV: (see --cand)  \n")
        fp.write("\n")

        # Per-strategy metrics
        fp.write("## Per-strategy metrics (overlap period)\n\n")
        fp.write("| Strategy | Net | PF | MaxDD | Ret/DD | Worst day | Worst week | Worst month | Active days | Win rate |\n")
        fp.write("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for n in names:
            m = per_strat[n]
            fp.write(f"| **{n}** | {fmt_money(m['net'])} | {m['pf']:.2f} "
                     f"| {fmt_money(m['max_dd'])} | {m['ret_dd']:.2f} "
                     f"| {fmt_money(m['worst_day'])} | {fmt_money(m['worst_week'])} "
                     f"| {fmt_money(m['worst_month'])} | {m['active_days']} | {m['win_rate']:.1%} |\n")
        fp.write("\n")

        # Correlation matrix
        fp.write("## Pearson correlation matrix (daily P&L)\n\n")
        fp.write("| | " + " | ".join(names) + " |\n")
        fp.write("|---|" + "|".join(["---:"] * len(names)) + "|\n")
        for a in names:
            cells = [f"**{a}**"]
            for b in names:
                cells.append(f"{corr_matrix[a][b]:+.3f}")
            fp.write("| " + " | ".join(cells) + " |\n")
        fp.write("\n")

        # Tom3 worst-day cushion
        if candidates:
            fp.write("## Tom3 worst-20-day cushion\n\n")
            fp.write("On Tom3's 20 worst days, what did each candidate contribute?\n\n")
            fp.write("| Candidate | Sum | Avg/day | Pos days | Neg days |\n")
            fp.write("|---|---:|---:|---:|---:|\n")
            for n in cand_names:
                c = cushion[n]
                fp.write(f"| **{n}** | {fmt_money(c['sum'])} | {fmt_money(c['avg'])} "
                         f"| {c['n_pos']} | {c['n_neg']} |\n")
            fp.write("\n")

        # Combo evaluation
        fp.write("## Portfolio combos (Tom3 + each candidate subset, 1×each)\n\n")
        fp.write("| Combo | Net | MaxDD | Ret/DD | Worst day | Worst week | Worst month | DD overlap days |\n")
        fp.write("|---|---:|---:|---:|---:|---:|---:|---:|\n")
        for c in sorted(combos, key=lambda x: -x["m"]["ret_dd"]):
            m = c["m"]
            fp.write(f"| **{c['label']}** | {fmt_money(m['net'])} "
                     f"| {fmt_money(m['max_dd'])} | {m['ret_dd']:.2f} "
                     f"| {fmt_money(m['worst_day'])} | {fmt_money(m['worst_week'])} "
                     f"| {fmt_money(m['worst_month'])} | {m['dd_overlap']} |\n")
        fp.write("\n")

        # Year-by-year
        fp.write("## Per-strategy yearly P&L\n\n")
        years = sorted({d.year for d in dates})
        fp.write("| Strategy | " + " | ".join(str(y) for y in years) + " |\n")
        fp.write("|---|" + "|".join(["---:"] * len(years)) + "|\n")
        for n in names:
            row = [f"**{n}**"]
            for y in years:
                row.append(fmt_money(year_breakdown[n].get(y, 0)))
            fp.write("| " + " | ".join(row) + " |\n")
        fp.write("\n")

        # Interpretation aids
        fp.write("## How to read this\n\n")
        fp.write("- **Ret/DD**: net / |MaxDD|. Higher = better risk-adjusted return.\n")
        fp.write("- **Worst day**: single biggest losing day across the period. For prop-firm survival this matters more than MaxDD.\n")
        fp.write("- **DD overlap days**: number of days when EVERY strategy in the combo was simultaneously below its peak. Lower = better diversification of drawdown timing.\n")
        fp.write("- **Tom3 worst-20 cushion**: if a candidate's `sum` is negative, it lost money on the days Tom3 needed help most — that's a red flag the average correlation misses.\n")
        fp.write("- **Pairwise correlation < 0.15** is the usual rule of thumb for "
                 "meaningful diversification; < 0.30 is acceptable.\n")

    print(f"\nWrote: {out}")


if __name__ == "__main__":
    main()
