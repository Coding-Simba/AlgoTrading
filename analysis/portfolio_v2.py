"""Tom3 vs NQ-candidate portfolio analysis — XML streaming version.

Parses unpacked xlsx XML directly via ElementTree.iterparse so we avoid
openpyxl's slow workbook-graph load on a 15 MB macro-enabled file.
"""

from __future__ import annotations
import csv
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean

sys.stdout.reconfigure(encoding="utf-8")

UNPACK = Path("/tmp/xlsm-extract/unpacked")
SHARED = UNPACK / "xl" / "sharedStrings.xml"
SHEET8 = UNPACK / "xl" / "worksheets" / "sheet8.xml"
TOM3_CSV = Path(r"\\Mac\Home\Documents\Samir strategies\NinjaTrader tom3 trades 2019 till 2026.csv")
OUT = Path(r"C:\Users\MAC\AlgoTrading\analysis\portfolio_results.md")

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Confirmed NQ candidates per Strategy Settings sheet
NQ_CANDIDATES = {
    "NQPivots", "Dipper", "MomentumNQ", "BlueLightning", "BlueLightningATR",
    "FBI", "Rumbler", "NQTrendFollower", "RedSword", "ClubBouncer",
    "FibScalper", "FerrisWheel", "OvernightCounter", "OneBarOneRule",
    "RatioBreakoutStrategy", "NasdaqHitter", "NQProp1", "MultiLL1",
    "OpeningRange(EHB)", "VReversalNQ", "GapFiller", "OpeningRange",
}


def load_shared_strings() -> list[str]:
    """Stream-parse sharedStrings.xml -> list of strings indexed 0..n."""
    strings: list[str] = []
    for _, elem in ET.iterparse(SHARED, events=("end",)):
        tag = elem.tag
        if tag == f"{NS}si":
            # collect all <t> text inside this <si> (handles rich text)
            text_parts = []
            for t in elem.iter(f"{NS}t"):
                text_parts.append(t.text or "")
            strings.append("".join(text_parts))
            elem.clear()
    return strings


def excel_serial_to_date(serial: float) -> date:
    """Excel's 1900-based date serial. Excel buggily counts 1900-02-29 so >=60 needs -1.
    Anchor: serial 1 = 1900-01-01. We use 1899-12-30 epoch which corrects the bug."""
    return (datetime(1899, 12, 30) + timedelta(days=int(serial))).date()


def col_letter_to_index(letters: str) -> int:
    """A -> 0, B -> 1, ..., AA -> 26."""
    idx = 0
    for ch in letters:
        if not ch.isalpha():
            break
        idx = idx * 26 + (ord(ch.upper()) - ord("A") + 1)
    return idx - 1


def stream_sheet8(shared: list[str]) -> tuple[list[date], dict[str, list[float]]]:
    """Stream rows from sheet8.xml. Returns (dates, {strategy_name: [pnl_per_date]})."""
    headers: list[str] = []
    dates: list[date] = []
    cols: dict[str, list[float]] = {}
    header_done = False
    max_cols = 0

    for _, elem in ET.iterparse(SHEET8, events=("end",)):
        if elem.tag != f"{NS}row":
            continue
        row_num = int(elem.get("r", "0"))
        # Collect cells: cell ref (e.g. "A2"), type, value
        cells: dict[int, str] = {}
        for c in elem.findall(f"{NS}c"):
            ref = c.get("r", "")
            t = c.get("t", "")
            v_el = c.find(f"{NS}v")
            v = v_el.text if v_el is not None and v_el.text else ""
            # is_el = c.find(f"{NS}is")  # inline string — unusual
            col_letters = "".join(ch for ch in ref if ch.isalpha())
            col = col_letter_to_index(col_letters)
            if t == "s":
                # shared string lookup
                try:
                    cells[col] = shared[int(v)]
                except (ValueError, IndexError):
                    cells[col] = ""
            else:
                cells[col] = v
        if not cells:
            elem.clear()
            continue

        if row_num == 1:
            # Header row
            max_cols = max(cells.keys()) + 1
            headers = [cells.get(c, "") for c in range(max_cols)]
            for h in headers[1:]:
                if h:
                    cols[h] = []
            header_done = True
        else:
            if not header_done:
                elem.clear()
                continue
            # First column = Period (date serial)
            d_str = cells.get(0, "")
            try:
                d_val = float(d_str)
                d = excel_serial_to_date(d_val)
            except (ValueError, TypeError):
                elem.clear()
                continue
            dates.append(d)
            for col_idx, h in enumerate(headers[1:], start=1):
                if not h:
                    continue
                v = cells.get(col_idx, "")
                try:
                    pnl = float(v) if v else 0.0
                except ValueError:
                    pnl = 0.0
                cols[h].append(pnl)
        elem.clear()
    return dates, cols


# ----- Tom3 CSV (same parser as before) -----

def parse_money(s: str) -> float:
    if not s:
        return 0.0
    s = s.strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    if not s:
        return 0.0
    return -float(s) if neg else float(s)


def load_tom3_daily() -> dict[date, float]:
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
                continue
            profit = parse_money(row.get("Profit", ""))
            d = dt.date()
            daily[d] = daily.get(d, 0.0) + profit
    return daily


# ----- analysis primitives -----

def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = (sum((x - mx) ** 2 for x in xs)) ** 0.5
    dy = (sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / (dx * dy) if dx and dy else 0.0


def drawdown_series(pnl: list[float]) -> list[float]:
    eq, peak = 0.0, 0.0
    dd = []
    for p in pnl:
        eq += p
        peak = max(peak, eq)
        dd.append(eq - peak)
    return dd


def metrics(pnl: list[float]) -> dict:
    if not pnl:
        return {"net": 0, "max_dd": 0, "n_days": 0}
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p < 0]
    dd = drawdown_series(pnl)
    active = sum(1 for p in pnl if p != 0)
    return {
        "net": sum(pnl),
        "pf": (sum(wins) / -sum(losses)) if losses else 0,
        "max_dd": min(dd) if dd else 0,
        "active_days": active,
        "win_days": len(wins),
        "loss_days": len(losses),
        "win_rate": (len(wins) / active) if active else 0,
        "ret_dd": (sum(pnl) / abs(min(dd))) if dd and min(dd) < 0 else 0,
    }


def worst_day_overlap(tom3: list[float], cand: list[float], top_n: int = 20) -> tuple[float, int, int]:
    paired = sorted(zip(tom3, cand), key=lambda x: x[0])[:top_n]
    return (sum(c for _, c in paired),
            sum(1 for _, c in paired if c > 0),
            sum(1 for _, c in paired if c < 0))


def dd_overlap_days(tom3: list[float], cand: list[float]) -> int:
    dd_a = drawdown_series(tom3)
    dd_b = drawdown_series(cand)
    return sum(1 for a, b in zip(dd_a, dd_b) if a < -1 and b < -1)


def main() -> None:
    print("Loading sharedStrings...")
    shared = load_shared_strings()
    print(f"  {len(shared)} strings")

    print("Streaming sheet8 (ChopPortfolio)...")
    dates, cols = stream_sheet8(shared)
    print(f"  {len(dates)} dates, {len(cols)} columns")

    print("Loading Tom3 trades...")
    tom3_daily = load_tom3_daily()
    print(f"  {len(tom3_daily)} active days, net ${sum(tom3_daily.values()):,.2f}")

    # Classify strategies
    nq_cols, other_cols = {}, {}
    for h, v in cols.items():
        h_norm = h.replace(" ", "")
        if any(c.replace(" ", "").lower() == h_norm.lower() for c in NQ_CANDIDATES):
            nq_cols[h] = v
        else:
            other_cols[h] = v
    print(f"  NQ-classified: {len(nq_cols)}: {sorted(nq_cols)}")

    tom3_aligned = [tom3_daily.get(d, 0.0) for d in dates]

    # Per-candidate analysis
    rows = []
    for name, pnl in sorted(nq_cols.items()):
        m = metrics(pnl)
        corr = pearson(tom3_aligned, pnl)
        wd_sum, wd_pos, wd_neg = worst_day_overlap(tom3_aligned, pnl)
        dd_ov = dd_overlap_days(tom3_aligned, pnl)
        pnl_2021 = sum(p for d, p in zip(dates, pnl) if d.year == 2021)
        pnl_2022 = sum(p for d, p in zip(dates, pnl) if d.year == 2022)
        pnl_2023 = sum(p for d, p in zip(dates, pnl) if d.year == 2023)
        pnl_2024 = sum(p for d, p in zip(dates, pnl) if d.year == 2024)
        pnl_2025 = sum(p for d, p in zip(dates, pnl) if d.year == 2025)
        rows.append({
            "name": name, "m": m, "corr": corr,
            "wd_sum": wd_sum, "wd_pos": wd_pos, "wd_neg": wd_neg,
            "dd_ov": dd_ov,
            "y2021": pnl_2021, "y2022": pnl_2022, "y2023": pnl_2023,
            "y2024": pnl_2024, "y2025": pnl_2025,
        })

    # Composite score
    for r in rows:
        own_score = 1.0 if r["m"]["net"] > 0 else (0.0 if r["m"]["net"] == 0 else -0.5)
        corr_score = max(0, 0.30 - abs(r["corr"])) / 0.30
        wd_score = min(1.0, max(-1.0, r["wd_sum"] / 5000.0))
        chop_score = 0.5 * ((1 if r["y2021"] > 0 else 0) + (1 if r["y2023"] > 0 else 0))
        r["score"] = own_score + corr_score + wd_score + chop_score

    rows.sort(key=lambda r: -r["score"])

    # Tom3 metrics
    tom3_full = sorted(tom3_daily.items())
    tom3_full_pnl = [v for _, v in tom3_full]
    tom3_full_m = metrics(tom3_full_pnl)
    tom3_overlap_m = metrics(tom3_aligned)
    tom3_year_pnl = {y: sum(v for d, v in tom3_full if d.year == y) for y in range(2019, 2027)}

    with OUT.open("w", encoding="utf-8") as fp:
        fp.write("# Tom3 vs NQ-candidate portfolio analysis\n\n")
        fp.write(f"Tom3 trades: 1048 (from `{TOM3_CSV.name}`). Workbook ChopPortfolio: {len(dates)} dates "
                 f"({dates[0]} to {dates[-1]}).\n\n")

        fp.write("## Tom3 baseline\n\n")
        fp.write("| | Full period (2019..2026) | Workbook overlap |\n|---|---:|---:|\n")
        fp.write(f"| Net | ${tom3_full_m['net']:,.0f} | ${tom3_overlap_m['net']:,.0f} |\n")
        fp.write(f"| PF  | {tom3_full_m['pf']:.2f} | {tom3_overlap_m['pf']:.2f} |\n")
        fp.write(f"| MaxDD | ${tom3_full_m['max_dd']:,.0f} | ${tom3_overlap_m['max_dd']:,.0f} |\n")
        fp.write(f"| Ret/DD | {tom3_full_m['ret_dd']:.2f} | {tom3_overlap_m['ret_dd']:.2f} |\n")
        fp.write(f"| Active days | {tom3_full_m['active_days']} | {tom3_overlap_m['active_days']} |\n")
        fp.write(f"| Win rate | {tom3_full_m['win_rate']:.2%} | {tom3_overlap_m['win_rate']:.2%} |\n\n")

        fp.write("### Tom3 yearly P&L (full period)\n\n")
        fp.write("| Year | Net |\n|---|---:|\n")
        for y in range(2019, 2027):
            fp.write(f"| {y} | ${tom3_year_pnl[y]:+,.0f} |\n")
        fp.write("\n")

        fp.write("## NQ candidates ranked by diversification score vs Tom3\n\n")
        fp.write("Score = own-profitability(±0.5/1) + low-corr-bonus(0..1) + Tom3-worst-day-cushion(±1) + chop-year(0.5 each for 2021 & 2023 positive).\n\n")
        fp.write("| # | Strategy | Net | PF | MaxDD | Ret/DD | Corr→Tom3 | Sum on Tom3 worst-20 | 2021 | 2022 | 2023 | 2024 | 2025 | **Score** |\n")
        fp.write("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for i, r in enumerate(rows, 1):
            m = r["m"]
            fp.write(f"| {i} | **{r['name']}** | ${m['net']:,.0f} | {m['pf']:.2f} | ${m['max_dd']:,.0f} | {m['ret_dd']:.2f} "
                     f"| {r['corr']:+.3f} | ${r['wd_sum']:+,.0f}({r['wd_pos']}+/{r['wd_neg']}-) "
                     f"| ${r['y2021']:+,.0f} | ${r['y2022']:+,.0f} | ${r['y2023']:+,.0f} "
                     f"| ${r['y2024']:+,.0f} | ${r['y2025']:+,.0f} "
                     f"| **{r['score']:+.2f}** |\n")

        fp.write("\n## Non-NQ / unclassified ChopPortfolio columns (skipped from NQ ranking)\n\n")
        for h in sorted(other_cols):
            m = metrics(other_cols[h])
            fp.write(f"- `{h}`: net=${m['net']:,.0f}, DD=${m['max_dd']:,.0f}, ret/dd={m['ret_dd']:.2f}\n")

        fp.write("\n## How to read it\n\n")
        fp.write("- **Corr→Tom3**: Pearson over the overlap period. Lower abs value = better.\n")
        fp.write("- **Sum on Tom3 worst-20**: total candidate P&L on the 20 worst Tom3 days. Positive = candidate cushioned the pain.\n")
        fp.write("- **Yearly P&L**: candidate's P&L per calendar year. Tom3 was weakest in 2021 and 2023.\n")
        fp.write("- **Score** is a heuristic. The actual decision should look at the row — net profit, drawdown overlap, chop-year P&L.\n")

    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
