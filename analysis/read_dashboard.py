"""Pull the key sheets from Samir's portfolio dashboard, UTF-8 safe."""

from __future__ import annotations
import sys
from pathlib import Path
from openpyxl import load_workbook

# Force UTF-8 output (Windows console default is cp1252)
sys.stdout.reconfigure(encoding="utf-8")

XLSM = Path(
    r"\\Mac\Home\Documents\Samir strategies\samir 700 dollar strategieen\Live_Portfolio_Dashboard_and_Settings_12.11.2025.xlsm"
)
OUT = Path(r"C:\Users\MAC\AlgoTrading\analysis\dashboard_dump.md")


def dump_sheet(ws, fp, max_rows: int = 80, max_cols: int = 20) -> None:
    fp.write(f"\n## `{ws.title}` (dim={ws.dimensions}, max_row={ws.max_row}, max_col={ws.max_column})\n\n")
    r_limit = min(ws.max_row or 0, max_rows)
    c_limit = min(ws.max_column or 0, max_cols)
    for r in range(1, r_limit + 1):
        row = []
        for c in range(1, c_limit + 1):
            v = ws.cell(r, c).value
            if v is None:
                row.append("")
            else:
                s = str(v).replace("\n", " ").strip()
                row.append(s[:60])
        if any(cell for cell in row):
            fp.write(f"R{r:>3}: " + " | ".join(row) + "\n")
    if (ws.max_row or 0) > max_rows:
        fp.write(f"... [{ws.max_row - max_rows} more rows truncated]\n")
    if (ws.max_column or 0) > max_cols:
        fp.write(f"... [{ws.max_column - max_cols} more cols truncated]\n")


def main() -> None:
    wb = load_workbook(XLSM, data_only=True, read_only=False, keep_vba=False)
    with OUT.open("w", encoding="utf-8") as fp:
        fp.write(f"# Dashboard dump — {XLSM.name}\n")
        fp.write(f"\nSheets ({len(wb.sheetnames)}): {', '.join(wb.sheetnames)}\n")

        priority = [
            "Instructions",
            "Strategy Settings",
            "Correlation",
            "Decay",
            "PortfolioCalculator",
            "ChopPortfolio",
            "PortfolioCalculatorOpt",
            "PropFirmPortfolio",
            "Equity",
            "Dipper",
            "GapFiller",
            "ESScalper",
            "NQTrendFollower",
        ]

        for name in priority:
            if name in wb.sheetnames:
                try:
                    dump_sheet(wb[name], fp)
                except Exception as e:
                    fp.write(f"\n## {name} (error: {e})\n")
            else:
                fp.write(f"\n[missing sheet: {name}]\n")

        # AllTrades — only header + first 30 trades + last 5 (don't dump 142k rows)
        if "AllTrades" in wb.sheetnames:
            ws = wb["AllTrades"]
            fp.write(f"\n## `AllTrades` HEADER + sample (full size {ws.max_row} x {ws.max_column})\n\n")
            c_limit = min(ws.max_column or 0, 21)
            for r in list(range(1, 31)) + list(range(max(2, ws.max_row - 4), ws.max_row + 1)):
                row = []
                for c in range(1, c_limit + 1):
                    v = ws.cell(r, c).value
                    if v is None:
                        row.append("")
                    else:
                        s = str(v).replace("\n", " ").strip()
                        row.append(s[:40])
                if any(cell for cell in row):
                    fp.write(f"R{r:>6}: " + " | ".join(row) + "\n")

    print(f"Wrote: {OUT}")
    print(f"Size: {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
