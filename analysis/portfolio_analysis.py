"""Tom3 vs NQ-candidate portfolio analysis.

Inputs:
- Tom3 trade-by-trade CSV from NT8 Strategy Analyzer (2019..2026)
- Live_Portfolio_Dashboard xlsm (ChopPortfolio sheet has per-strategy daily P&L)

Outputs:
- daily P&L series per strategy (Tom3 + all workbook candidates)
- correlation matrix vs Tom3 (overlap period)
- drawdown-overlap analysis (days/months both losing)
- worst-day overlap (top-N worst Tom3 days, what did each candidate do)
- chop-year performance (2021, 2023, when Tom3 was weak)
- composite diversification score per candidate

Saves results to portfolio_results.md.
"""

from __future__ import annotations
import csv
import re
import sys
from datetime import date, datetime
from pathlib import Path
from statistics import mean, stdev

from openpyxl import load_workbook

sys.stdout.reconfigure(encoding="utf-8")

TOM3_CSV = Path(r"\\Mac\Home\Documents\Samir strategies\NinjaTrader tom3 trades 2019 till 2026.csv")
XLSM = Path(r"\\Mac\Home\Documents\Samir strategies\samir 700 dollar strategieen\Live_Portfolio_Dashboard_and_Settings_12.11.2025.xlsm")
OUT = Path(r"C:\Users\MAC\AlgoTrading\analysis\portfolio_results.md")

# Strategies that trade NQ (or could) per Strategy Settings sheet:
NQ_CANDIDATES = {
    "NQPivots", "Dipper", "MomentumNQ", "BlueLightning", "BlueLightningATR",
    "FBI", "Rumbler", "NQTrendFollower", "VWAPBouncer", "RedSword", "Red Sword",
    "ClubBouncer", "Club Bouncer", "FibScalper", "FerrisWheel", "Ferris Wheel",
    "OvernightCounter", "OneBarOneRule", "RatioBreakoutStrategy", "NasdaqHitter",
    "NQProp1", "MultiLL1", "OpeningRange(EHB)", "OpeningRange", "VReversalNQ",
    "GapFiller",
}

# Strategies known NOT to be NQ (skip from ChopPortfolio columns):
NON_NQ = {
    "VariableTrend", "ESSniper", "ESScalper", "GoldLiquid", "BlackGas",
    "Watchmen", "JamesBond", "VioletScimitar", "LunchSnacker", "CatalyticReverter",
    "TexasTea", "Tanker", "WaveRider", "VWAPBouncer", "DipperV2", "VReversalES",
    "ExGF", "ExBF", "DowJumper", "EarlyNight", "ESOvernightEuro", "SkyShark",
    "Snowball", "SilverLining", "CrudeCrown", "Polluter", "Goldsmith",
    "TrendFollowerGold", "VReversalRTY",
}


def parse_money(s: str) -> float:
    """Handle '$1234.56', '($1234.56)', '$0.00', or empty."""
    if not s:
        return 0.0
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    if not s:
        return 0.0
    v = float(s)
    return -v if neg else v


def load_tom3_daily() -> dict[date, float]:
    """Aggregate Tom3 trades by Exit date -> realized P&L (net of commission)."""
    daily: dict[date, float] = {}
    with TOM3_CSV.open("r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            exit_time = row.get("Exit time", "").strip()
            if not exit_time:
                continue
            try:
                dt = datetime.strptime(exit_time, "%m/%d/%Y %I:%M:%S %p")
            except ValueError:
                try:
                    dt = datetime.strptime(exit_time, "%m/%d/%Y %H:%M:%S")
                except ValueError:
                    continue
            profit = parse_money(row.get("Profit", ""))
            # net of fees if present (mostly $0.00 here)
            fees = sum(parse_money(row.get(k, "")) for k in (
                "Commission", "Clearing Fee", "Exchange Fee", "IP Fee", "NFA Fee"
            ))
            net = profit - fees
            d = dt.date()
            daily[d] = daily.get(d, 0.0) + net
    return daily


def load_workbook_daily() -> tuple[list[date], dict[str, list[float]]]:
    """Read ChopPortfolio sheet -> per-strategy daily P&L vectors aligned on dates."""
    wb = load_workbook(XLSM, data_only=True, read_only=True)
    ws = wb["ChopPortfolio"]
    # Row 1 is header
    headers = []
    for c in range(1, ws.max_column + 1):
        v = ws.cell(1, c).value
        headers.append(str(v) if v else "")
    # Column 1 = date (Period)
    dates: list[date] = []
    cols: dict[str, list[float]] = {h: [] for h in headers[1:] if h}

    for r in range(2, ws.max_row + 1):
        d = ws.cell(r, 1).value
        if not d:
            continue
        if isinstance(d, datetime):
            d = d.date()
        if not isinstance(d, date):
            continue
        dates.append(d)
        for c, h in enumerate(headers[1:], start=2):
            if not h:
                continue
            v = ws.cell(r, c).value
            try:
                cols[h].append(float(v) if v is not None else 0.0)
            except (TypeError, ValueError):
                cols[h].append(0.0)
    return dates, cols


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def drawdown_series(pnl: list[float]) -> list[float]:
    """Cumulative equity and underwater (drawdown) series."""
    eq, peak = 0.0, 0.0
    dd = []
    for p in pnl:
        eq += p
        peak = max(peak, eq)
        dd.append(eq - peak)
    return dd


def metrics(pnl: list[float]) -> dict:
    if not pnl:
        return {"net": 0, "max_dd": 0, "n_days": 0, "win_days": 0, "loss_days": 0}
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p < 0]
    dd = drawdown_series(pnl)
    return {
        "net": sum(pnl),
        "gross_win": sum(wins),
        "gross_loss": sum(losses),
        "pf": (sum(wins) / -sum(losses)) if losses and sum(losses) != 0 else 0,
        "max_dd": min(dd) if dd else 0,
        "n_days": len(pnl),
        "win_days": len(wins),
        "loss_days": len(losses),
        "active_days": sum(1 for p in pnl if p != 0),
        "win_rate_active": (len(wins) / sum(1 for p in pnl if p != 0)) if any(p != 0 for p in pnl) else 0,
        "avg_day": mean(pnl),
        "ret_dd": (sum(pnl) / abs(min(dd))) if dd and min(dd) < 0 else float("inf") if sum(pnl) > 0 else 0,
    }


def worst_day_overlap(tom3: list[float], cand: list[float], top_n: int = 20) -> tuple[float, int, int]:
    """For top_n worst Tom3 days, sum the candidate's P&L on those same days.
    Returns (sum, n_positive_days, n_negative_days)."""
    paired = sorted(zip(tom3, cand), key=lambda x: x[0])[:top_n]
    return (sum(c for _, c in paired),
            sum(1 for _, c in paired if c > 0),
            sum(1 for _, c in paired if c < 0))


def dd_overlap_days(tom3: list[float], cand: list[float]) -> int:
    """Days both Tom3 and candidate are in drawdown (below their respective peaks)."""
    dd_a = drawdown_series(tom3)
    dd_b = drawdown_series(cand)
    return sum(1 for a, b in zip(dd_a, dd_b) if a < -1 and b < -1)


def main() -> None:
    print("Loading Tom3 trades...")
    tom3_daily = load_tom3_daily()
    print(f"  Tom3: {len(tom3_daily)} active days")
    print(f"  Net (sum of daily): ${sum(tom3_daily.values()):,.2f}")

    print("Loading workbook ChopPortfolio...")
    dates, cols = load_workbook_daily()
    print(f"  Workbook: {len(dates)} dates, {len(cols)} strategy columns")

    # Filter to NQ candidates only (case-insensitive match)
    def is_nq(h: str) -> bool:
        h_norm = h.replace(" ", "")
        for cand in NQ_CANDIDATES:
            if cand.replace(" ", "").lower() == h_norm.lower():
                return True
        for non in NON_NQ:
            if non.replace(" ", "").lower() == h_norm.lower():
                return False
        # Unknown — include with "?" marker
        return None  # type: ignore

    nq_cols = {h: v for h, v in cols.items() if is_nq(h) is True}
    unknown_cols = {h: v for h, v in cols.items() if is_nq(h) is None}
    print(f"  Confirmed NQ: {len(nq_cols)}  ({sorted(nq_cols)})")
    print(f"  Unknown (skipped from ranking): {len(unknown_cols)}  ({sorted(unknown_cols)[:10]}{'...' if len(unknown_cols) > 10 else ''})")

    # Align Tom3 with workbook dates
    tom3_aligned = [tom3_daily.get(d, 0.0) for d in dates]

    # Tom3 metrics over the workbook overlap period
    tom3_overlap_metrics = metrics(tom3_aligned)
    # Tom3 full-period metrics
    tom3_full = sorted(tom3_daily.items())
    tom3_full_pnl = [v for _, v in tom3_full]
    tom3_full_metrics = metrics(tom3_full_pnl)

    # Per-candidate analysis
    results = []
    for name, pnl in sorted(nq_cols.items()):
        m = metrics(pnl)
        corr = pearson(tom3_aligned, pnl)
        wdo_sum, wdo_pos, wdo_neg = worst_day_overlap(tom3_aligned, pnl, top_n=20)
        dd_overlap = dd_overlap_days(tom3_aligned, pnl)

        # 2021 and 2023 chop-year P&L
        pnl_2021 = sum(p for d, p in zip(dates, pnl) if d.year == 2021)
        pnl_2023 = sum(p for d, p in zip(dates, pnl) if d.year == 2023)
        tom3_2021 = sum(p for d, p in zip(dates, tom3_aligned) if d.year == 2021)
        tom3_2023 = sum(p for d, p in zip(dates, tom3_aligned) if d.year == 2023)

        results.append({
            "name": name,
            "metrics": m,
            "corr": corr,
            "worst20_sum": wdo_sum,
            "worst20_pos": wdo_pos,
            "worst20_neg": wdo_neg,
            "dd_overlap_days": dd_overlap,
            "pnl_2021": pnl_2021,
            "pnl_2023": pnl_2023,
            "tom3_2021": tom3_2021,
            "tom3_2023": tom3_2023,
        })

    # Composite diversification score: higher = better complement to Tom3
    # Components: own net positive, low correlation, positive sum on Tom3's worst days, positive in chop years
    for r in results:
        own_score = 1.0 if r["metrics"]["net"] > 0 else -0.5
        corr_score = max(0, 0.30 - abs(r["corr"])) / 0.30  # 1.0 if corr <= 0, 0 if corr=0.30+
        wdo_score = min(1.0, max(-1.0, r["worst20_sum"] / 5000.0))  # +1 if covers $5K of Tom3 worst-day losses
        chop_2021 = 1.0 if r["pnl_2021"] > 0 else 0
        chop_2023 = 1.0 if r["pnl_2023"] > 0 else 0
        r["score"] = own_score + corr_score + wdo_score + 0.5 * (chop_2021 + chop_2023)

    results.sort(key=lambda r: -r["score"])

    # Write report
    with OUT.open("w", encoding="utf-8") as fp:
        fp.write("# Tom3 vs NQ-candidate portfolio analysis\n\n")
        fp.write(f"- Tom3 trades CSV: `{TOM3_CSV.name}` — 1048 trades, "
                 f"net ${sum(tom3_daily.values()):,.2f}\n")
        fp.write(f"- Workbook: `{XLSM.name}` ChopPortfolio sheet — {len(dates)} dates "
                 f"(`{dates[0]}` to `{dates[-1]}`)\n")
        fp.write(f"- Tom3 active days: {len(tom3_daily)} (full period); "
                 f"{sum(1 for v in tom3_aligned if v != 0)} (overlap period {dates[0]}..{dates[-1]})\n\n")

        fp.write("## Tom3 baseline\n\n")
        fp.write("| Metric | Full period (2019-2026) | Overlap period (workbook dates) |\n")
        fp.write("|---|---|---|\n")
        fp.write(f"| Net | ${tom3_full_metrics['net']:,.0f} | ${tom3_overlap_metrics['net']:,.0f} |\n")
        fp.write(f"| Max DD | ${tom3_full_metrics['max_dd']:,.0f} | ${tom3_overlap_metrics['max_dd']:,.0f} |\n")
        fp.write(f"| Ret/DD | {tom3_full_metrics['ret_dd']:.2f} | {tom3_overlap_metrics['ret_dd']:.2f} |\n")
        fp.write(f"| Active days | {tom3_full_metrics['active_days']} | {tom3_overlap_metrics['active_days']} |\n")
        fp.write(f"| Win-day rate | {tom3_full_metrics['win_rate_active']:.2%} | {tom3_overlap_metrics['win_rate_active']:.2%} |\n")
        fp.write(f"| 2021 P&L | ${sum(p for d, p in tom3_full if d.year == 2021):,.0f} | — |\n")
        fp.write(f"| 2023 P&L | ${sum(p for d, p in tom3_full if d.year == 2023):,.0f} | — |\n\n")

        fp.write("## NQ candidates ranked by diversification value vs Tom3\n\n")
        fp.write("Score components: own profitability (1pt) + low correlation (0-1pt) + "
                 "positive sum on Tom3's 20 worst days (-1..1pt) + positive in 2021/2023 (0.5pt each).\n\n")
        fp.write("| # | Strategy | Net | Max DD | Ret/DD | Corr to Tom3 | Sum on Tom3 worst-20 | DD overlap days | 2021 P&L | 2023 P&L | **Score** |\n")
        fp.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for i, r in enumerate(results, 1):
            m = r["metrics"]
            fp.write(f"| {i} | **{r['name']}** | ${m['net']:,.0f} | ${m['max_dd']:,.0f} "
                     f"| {m['ret_dd']:.2f} | {r['corr']:+.3f} "
                     f"| ${r['worst20_sum']:+,.0f} ({r['worst20_pos']}pos/{r['worst20_neg']}neg) "
                     f"| {r['dd_overlap_days']} "
                     f"| ${r['pnl_2021']:+,.0f} | ${r['pnl_2023']:+,.0f} "
                     f"| **{r['score']:+.2f}** |\n")

        fp.write("\n## Unknown / unclassified strategies in ChopPortfolio (instrument unverified)\n\n")
        for name in sorted(unknown_cols):
            m = metrics(unknown_cols[name])
            fp.write(f"- `{name}`: net=${m['net']:,.0f}, DD=${m['max_dd']:,.0f}\n")

        fp.write("\n## Notes on metrics\n\n")
        fp.write("- **Corr to Tom3**: Pearson over the overlap period using daily P&L. Lower = better.\n")
        fp.write("- **Sum on Tom3 worst-20**: P&L the candidate made/lost on the 20 worst Tom3 days. POSITIVE = candidate cushioned Tom3's worst days. NEGATIVE = candidate lost too.\n")
        fp.write("- **DD overlap days**: Days both Tom3 AND candidate were below their respective equity peaks. Lower = better drawdowns happened at different times.\n")
        fp.write("- **2021 / 2023 P&L**: Tom3's weakest years per audit. A good complement makes money here.\n")

    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
