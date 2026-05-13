"""Map workbook strategy names to actual .cs files in the folder.

For each .cs file, extract:
- public class name
- Display Name (from SetDefaults `Name = "..."` line)
- whether it uses AddDataSeries for multi-timeframe
- whether it uses ATR / EMA / RSI / Bollinger / SMA
- whether it has SetStopLoss / SetProfitTarget / SetTrailStop
- presence of martingale-style logic (e.g. doubling quantity after loss)

Then cross-reference against the workbook's Strategy Settings sheet.
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

FOLDER = Path(r"\\Mac\Home\Documents\Samir strategies\samir 700 dollar strategieen")
OUT = Path(r"C:\Users\MAC\AlgoTrading\analysis\strategy_map.md")

# Workbook strategy names of interest (NQ-only or potentially NQ)
WORKBOOK_NQ = [
    "NQPivots", "Dipper", "MomentumNQ", "BlueLightning", "BlueLightningATR",
    "FBI", "Rumbler", "NQTrendFollower", "VWAPBouncer", "Red Sword",
    "Club Bouncer", "FibScalper", "Ferris Wheel", "OvernightCounter",
    "OneBarOneRule", "RatioBreakoutStrategy", "NasdaqHitter", "NQProp1",
    "MultiLL1", "OpeningRange(EHB)", "VReversalNQ", "GapFiller",
]

# Patterns to identify
PAT_CLASS = re.compile(r"public\s+class\s+(\w+)\s*:\s*Strategy")
PAT_NAME = re.compile(r'Name\s*=\s*"([^"]+)"')
PAT_DESC = re.compile(r'Description\s*=\s*@?"([^"]+)"')
PAT_ADD_DATA = re.compile(r"AddDataSeries\s*\(\s*(?:Data\.)?BarsPeriodType\.(\w+)\s*,\s*(\d+)")
PAT_SET_STOP = re.compile(r"SetStopLoss\s*\(([^)]+)\)")
PAT_SET_TP = re.compile(r"SetProfitTarget\s*\(([^)]+)\)")
PAT_SET_TRAIL = re.compile(r"SetTrailStop\s*\(([^)]+)\)")


def classify_file(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"file": path.name, "error": str(e)}

    cls = PAT_CLASS.search(text)
    name = PAT_NAME.search(text)
    desc = PAT_DESC.search(text)
    add_data = PAT_ADD_DATA.findall(text)
    sl = PAT_SET_STOP.findall(text)
    tp = PAT_SET_TP.findall(text)
    trail = PAT_SET_TRAIL.findall(text)

    indicators = []
    for ind in ["EMA", "SMA", "RSI", "Bollinger", "ATR", "ADX", "MACD", "Stochastics", "VWAP", "WilliamsR", "DM", "DMI", "Pivots", "VOL"]:
        if re.search(rf"\b{ind}\s*\(", text):
            indicators.append(ind)

    # Heuristic martingale detection: doubling quantity, EnterLong/Short with size>1 after loss
    has_doubling = bool(re.search(r"(quantity|qty|size|contracts).*\*=?\s*2\b", text, re.IGNORECASE))
    has_dca = bool(re.search(r"\bDCA\b|averageDown|addToPosition", text, re.IGNORECASE))

    has_session_close = "IsExitOnSessionCloseStrategy" in text and "= true" in text.lower().replace(" ", "")
    has_session_iterator = "SessionIterator" in text

    has_account_logic = bool(re.search(r"Account\.\w+\s*\(", text)) or "Account.All" in text
    is_risk_wrapper = (
        ("Flatten" in text and "Account" in text)
        or any(s in path.name.lower() for s in ["portfoliotrail", "stopat", "dailyprofit", "closeallendofday", "topstepscalecounter", "openpnlrule"])
    )

    return {
        "file": path.name,
        "class": cls.group(1) if cls else "?",
        "name": name.group(1) if name else "?",
        "indicators": ",".join(indicators) or "-",
        "add_data": "; ".join(f"{a[0]}{a[1]}" for a in add_data) or "-",
        "set_sl": sl[0][:50] if sl else "-",
        "set_tp": tp[0][:50] if tp else "-",
        "set_trail": trail[0][:50] if trail else "-",
        "martingale": "Y" if has_doubling or has_dca else "-",
        "session_close": "Y" if has_session_close else "-",
        "is_risk_wrapper": is_risk_wrapper,
        "is_account_logic": has_account_logic,
        "lines": len(text.splitlines()),
    }


def main() -> None:
    files = sorted(FOLDER.glob("*.cs"))
    results = [classify_file(f) for f in files if not f.name.startswith("@")]

    with OUT.open("w", encoding="utf-8") as fp:
        fp.write("# Strategy file map\n\n")
        fp.write(f"Folder: `{FOLDER}`\n")
        fp.write(f"Total non-sample .cs files: {len(results)}\n\n")

        # Section 1: identified strategies (not risk wrappers)
        strats = [r for r in results if not r.get("is_risk_wrapper")]
        fp.write(f"## Strategy files ({len(strats)})\n\n")
        fp.write("| File | Class | Display Name | Indicators | AddDataSeries | SL | TP | Trail | Martingale? | Lines |\n")
        fp.write("|------|-------|--------------|------------|---------------|----|----|-------|-------------|-------|\n")
        for r in strats:
            fp.write(f"| `{r['file']}` | {r['class']} | {r['name']} | {r['indicators']} | {r['add_data']} | {r['set_sl']} | {r['set_tp']} | {r['set_trail']} | {r['martingale']} | {r['lines']} |\n")

        # Section 2: risk wrappers
        wrappers = [r for r in results if r.get("is_risk_wrapper")]
        fp.write(f"\n## Risk wrappers (account-level, not strategies) ({len(wrappers)})\n\n")
        for r in wrappers:
            fp.write(f"- `{r['file']}` -> {r['class']} -> Name=\"{r['name']}\"  ({r['lines']} lines)\n")

        # Section 3: name-matching for NQ candidates
        fp.write(f"\n## Workbook NQ candidate -> .cs file matching\n\n")
        fp.write("| Workbook name | Best .cs match | Confidence | Notes |\n")
        fp.write("|---------------|----------------|------------|-------|\n")
        names_by_lower = {}
        for r in results:
            for tok in (r["file"].lower().replace(".cs", ""), r["class"].lower(), r["name"].lower()):
                names_by_lower.setdefault(tok, []).append(r)

        def find_match(target: str) -> tuple[str, str, str]:
            t_low = target.lower().replace(" ", "")
            # exact
            for key, recs in names_by_lower.items():
                if key.replace(" ", "") == t_low:
                    return (recs[0]["file"], "exact", f"class={recs[0]['class']} name={recs[0]['name']}")
            # contains
            for key, recs in names_by_lower.items():
                if t_low in key.replace(" ", "") or key.replace(" ", "") in t_low:
                    return (recs[0]["file"], "partial", f"class={recs[0]['class']} name={recs[0]['name']}")
            return ("", "MISSING", "no candidate found in folder")

        for wb_name in WORKBOOK_NQ:
            f, conf, notes = find_match(wb_name)
            fp.write(f"| {wb_name} | {f or '—'} | {conf} | {notes} |\n")

    print(f"Wrote: {OUT}")


if __name__ == "__main__":
    main()
