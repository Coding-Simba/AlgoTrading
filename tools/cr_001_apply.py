"""CR-001 apply script.

Mechanizes the changes proposed by
``docs/change_requests/CR-001_v0.3_v0.4_registration_and_capital.md`` once
the CR has been countersigned by both Director Sponsor (DIR-01) and an
independent Risk Reviewer (RISK-01).

The script is intentionally narrow: it does *only* what CR-001 specifies,
refuses on any precondition failure, and is idempotent (safe to re-run).
There is no override flag.

Steps:
    register-strategies   — append v0.3 / v0.4 to registry + signoff matrix.
    raise-capital         — update risk_limits.yml (gated on `paper` row signed).

Usage:
    python tools/cr_001_apply.py --step register-strategies [--dry-run]
    python tools/cr_001_apply.py --step raise-capital      [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CR_PATH = REPO_ROOT / "docs" / "change_requests" / "CR-001_v0.3_v0.4_registration_and_capital.md"
SPEC_V3_PATH = REPO_ROOT / "docs" / "appendices" / "B_strategy_spec_v0_3.md"
SPEC_V4_PATH = REPO_ROOT / "docs" / "appendices" / "B_strategy_spec_v0_4.md"
REGISTRY_PATH = REPO_ROOT / "configs" / "strategy_registry.jsonl"
SIGNOFF_MATRIX_PATH = REPO_ROOT / "configs" / "signoff_matrix.yml"
RISK_LIMITS_PATH = REPO_ROOT / "configs" / "risk_limits.yml"
CONTAMINATION_LOG_PATH = REPO_ROOT / "docs" / "research_contamination_log" / "research_contamination_log.csv"

SIGNOFF_BLOCK_RE = re.compile(
    r"```yaml\n# CR-001 SIGNOFFS\n(?P<body>.*?)```",
    re.DOTALL,
)

_NEW_SIGNOFF_ROWS_BLOCK = """
  - id: "B_v0.3"
    title: "Appendix B v0.3 — strategy specification (mean-reversion to VWAP)"
    signer_role: "Director sponsor"
    required_for: "v0.3_code"
    signed: false
    signed_by: ""
    signed_at_iso: ""
    notes: "Added by CR-001. Strategy code is gate-blocked until this row is signed by DIR-01."

  - id: "B_v0.4"
    title: "Appendix B v0.4 — regime classifier + switch policy"
    signer_role: "Director sponsor"
    required_for: "v0.4_code"
    signed: false
    signed_by: ""
    signed_at_iso: ""
    notes: "Added by CR-001. Switch-policy code is gate-blocked until this row is signed by DIR-01."
"""


class CrApplyError(RuntimeError):
    pass


def _is_iso8601(value: str) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _read_signoffs(cr_text: str) -> dict[str, dict[str, str]]:
    m = SIGNOFF_BLOCK_RE.search(cr_text)
    if not m:
        raise CrApplyError(
            "CR-001 sign-off block not found. Expected a fenced YAML block "
            "starting with `# CR-001 SIGNOFFS`."
        )
    body = "# CR-001 SIGNOFFS\n" + m.group("body")
    parsed = yaml.safe_load(body) or {}
    if not isinstance(parsed, dict):
        raise CrApplyError("CR-001 sign-off block did not parse as a mapping.")
    out: dict[str, dict[str, str]] = {}
    for key in ("director_sponsor", "risk_reviewer"):
        block = parsed.get(key) or {}
        if not isinstance(block, dict):
            raise CrApplyError(f"CR-001 sign-off block: {key} must be a mapping.")
        out[key] = {
            "signer_id": str(block.get("signer_id") or "").strip(),
            "signed_at_iso": str(block.get("signed_at_iso") or "").strip(),
        }
    return out


def _require_countersigns(cr_text: str) -> dict[str, dict[str, str]]:
    s = _read_signoffs(cr_text)
    ds = s["director_sponsor"]
    rr = s["risk_reviewer"]
    errors: list[str] = []
    if not ds["signer_id"]:
        errors.append("director_sponsor.signer_id is empty")
    if not _is_iso8601(ds["signed_at_iso"]):
        errors.append("director_sponsor.signed_at_iso is not ISO-8601")
    if not rr["signer_id"]:
        errors.append("risk_reviewer.signer_id is empty")
    if not _is_iso8601(rr["signed_at_iso"]):
        errors.append("risk_reviewer.signed_at_iso is not ISO-8601")
    if ds["signer_id"] and rr["signer_id"] and ds["signer_id"] == rr["signer_id"]:
        errors.append(
            "director_sponsor and risk_reviewer must be different identities "
            "(independence rule, docs/OWNERS.md)"
        )
    if errors:
        raise CrApplyError(
            "CR-001 not countersigned; cannot apply. Issues: " + "; ".join(errors)
        )
    return s


def _hash_rules(rules: dict[str, Any]) -> str:
    payload = json.dumps(rules, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _registry_entries() -> list[dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in REGISTRY_PATH.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(json.loads(raw))
    return out


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_v03_rules() -> dict[str, Any]:
    return {
        "spec_appendix": "B_v0.3",
        "spec_md_path": "docs/appendices/B_strategy_spec_v0_3.md",
        "spec_md_sha256": _file_sha256(SPEC_V3_PATH),
        "family": "MES_intraday",
        "edge_class": "mean_reversion_to_session_vwap",
        "instrument": "MES",
        "session": "RTH",
        "signal_window_open_et": "10:35",
        "signal_window_close_et": "15:30",
        "forced_flat_et": "15:58",
        "max_trades_per_session_combined_with_v02": 3,
        "max_open_positions_combined_with_v02": 1,
        "extension_atr_multiplier": 1.5,
        "stop_atr_multiplier_min": 0.5,
        "stop_atr_multiplier_max": 1.5,
        "stalling_pattern": "signal_bar_extreme_does_not_extend",
        "wick_rejection_fraction": 0.3,
        "trend_alignment": "non_aligned_only",
        "target": "session_vwap_at_fill_time",
    }


def _build_v04_rules() -> dict[str, Any]:
    return {
        "spec_appendix": "B_v0.4",
        "spec_md_path": "docs/appendices/B_strategy_spec_v0_4.md",
        "spec_md_sha256": _file_sha256(SPEC_V4_PATH),
        "family": "MES_intraday",
        "edge_class": "regime_classifier_and_switch",
        "labels": ["TREND", "MEANREV", "NEUTRAL"],
        "switch_policy": {
            "TREND": "v0.2",
            "MEANREV": "v0.3",
            "NEUTRAL": None,
        },
        "trend_strength_threshold_strong": 0.0030,
        "trend_strength_threshold_weak": 0.0010,
        "vol_norm_threshold_low": 0.0008,
        "vwap_dev_threshold_strong": 1.5,
        "evaluation_cadence": "per_60m_close",
        "consumes_validation_partitions": False,
    }


def _registry_already_has(version: str, rules_hash: str) -> bool:
    for e in _registry_entries():
        if e.get("strategy_version") == version and e.get("rules_hash") == rules_hash:
            return True
    return False


def _append_registry_entry(
    *,
    strategy_version: str,
    family: str,
    rules: dict[str, Any],
    registered_by: str,
    registered_at: str,
    dry_run: bool,
) -> dict[str, Any]:
    rules_hash = _hash_rules(rules)
    if _registry_already_has(strategy_version, rules_hash):
        return {"status": "already_present", "strategy_version": strategy_version}
    entry_id = hashlib.sha256(
        f"{registered_at}|{strategy_version}|{rules_hash}".encode()
    ).hexdigest()[:16]
    entry = {
        "entry_id": entry_id,
        "registered_at": registered_at,
        "strategy_version": strategy_version,
        "family": family,
        "rules_hash": rules_hash,
        "rules": rules,
        "registered_by": registered_by,
        "note": "Registered via CR-001 (pre-v0.2-OOS, §B.13 clean ordering).",
        "supersedes": None,
    }
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"))
    if dry_run:
        print(f"[dry-run] APPEND to {REGISTRY_PATH.relative_to(REPO_ROOT)}: {line}")
        return {"status": "would_append", "entry_id": entry_id}
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
    return {"status": "appended", "entry_id": entry_id}


def _signoff_matrix_already_has_rows(text: str) -> bool:
    return 'id: "B_v0.3"' in text and 'id: "B_v0.4"' in text


def _append_signoff_rows(*, dry_run: bool) -> dict[str, Any]:
    text = SIGNOFF_MATRIX_PATH.read_text(encoding="utf-8")
    if _signoff_matrix_already_has_rows(text):
        return {"status": "already_present"}
    new_text = text
    if not new_text.endswith("\n"):
        new_text += "\n"
    new_text += _NEW_SIGNOFF_ROWS_BLOCK
    if dry_run:
        print(
            f"[dry-run] APPEND rows B_v0.3 and B_v0.4 to "
            f"{SIGNOFF_MATRIX_PATH.relative_to(REPO_ROOT)}"
        )
        return {"status": "would_append"}
    SIGNOFF_MATRIX_PATH.write_text(new_text, encoding="utf-8")
    return {"status": "appended"}


def _append_contamination_row(
    *, signers: dict[str, dict[str, str]], dry_run: bool
) -> dict[str, Any]:
    if not CONTAMINATION_LOG_PATH.exists():
        raise CrApplyError(
            f"contamination log not found at {CONTAMINATION_LOG_PATH}; cannot append."
        )
    description = (
        "Registered v0.3 (mean-reversion to VWAP) and v0.4 (regime "
        "classifier + switch) per CR-001 §B.13. "
        f"Director sponsor: {signers['director_sponsor']['signer_id']}; "
        f"Risk reviewer: {signers['risk_reviewer']['signer_id']}. "
        "v0.2 OOS partition has not yet been queried; v0.3 inherits clean "
        "OOS partition per §B.13."
    )
    row = [
        _now_iso(),
        "cr-001-apply",
        "v0.3+v0.4",
        "rule_change",
        description,
        "none",
        "N/A",
        "logged_for_next_version",
        "",
        "",
    ]
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_MINIMAL, lineterminator="\n").writerow(row)
    line = buf.getvalue()
    if dry_run:
        print(
            f"[dry-run] APPEND to {CONTAMINATION_LOG_PATH.relative_to(REPO_ROOT)}: "
            f"{line.rstrip()}"
        )
        return {"status": "would_append"}
    existing = CONTAMINATION_LOG_PATH.read_text(encoding="utf-8")
    if existing and not existing.endswith("\n"):
        existing += "\n"
    CONTAMINATION_LOG_PATH.write_text(existing + line, encoding="utf-8")
    return {"status": "appended"}


def _step_register_strategies(*, dry_run: bool) -> int:
    cr_text = CR_PATH.read_text(encoding="utf-8")
    signers = _require_countersigns(cr_text)
    registered_by = "cr-001-apply"
    registered_at = _now_iso()

    print(
        f"register-strategies (dry_run={dry_run}): countersigns OK "
        f"(DIR={signers['director_sponsor']['signer_id']}, "
        f"RISK={signers['risk_reviewer']['signer_id']})"
    )

    r1 = _append_registry_entry(
        strategy_version="v0.3",
        family="MES_intraday",
        rules=_build_v03_rules(),
        registered_by=registered_by,
        registered_at=registered_at,
        dry_run=dry_run,
    )
    print(f"  v0.3 registry: {r1}")

    r2 = _append_registry_entry(
        strategy_version="v0.4",
        family="MES_intraday",
        rules=_build_v04_rules(),
        registered_by=registered_by,
        registered_at=registered_at,
        dry_run=dry_run,
    )
    print(f"  v0.4 registry: {r2}")

    r3 = _append_signoff_rows(dry_run=dry_run)
    print(f"  signoff_matrix rows: {r3}")

    r4 = _append_contamination_row(signers=signers, dry_run=dry_run)
    print(f"  contamination_log: {r4}")

    return 0


def _step_raise_capital(*, dry_run: bool) -> int:
    cr_text = CR_PATH.read_text(encoding="utf-8")
    signers = _require_countersigns(cr_text)

    matrix = yaml.safe_load(SIGNOFF_MATRIX_PATH.read_text(encoding="utf-8")) or {}
    rows = (matrix.get("rows") if isinstance(matrix, dict) else None) or []
    paper_row = next(
        (r for r in rows if isinstance(r, dict) and r.get("id") == "paper"), None
    )
    if paper_row is None or not paper_row.get("signed"):
        raise CrApplyError(
            "raise-capital blocked: 'paper' row in signoff_matrix.yml is not "
            "signed. Per CR-001 §6, capital raise is conditional on paper "
            "sign-off."
        )

    new_yaml = (
        "# Risk limits — raised per CR-001 §6. These values supersede the\n"
        "# original v1.4-r1 values; rollback requires a new CR (see CR-001 §9).\n"
        "# Director sponsor signs the capital raise; Risk Reviewer countersigns.\n"
        "# Editing locked values still requires a future Change Request.\n\n"
        "allocated_capital_usd: 5000\n"
        "max_oos_drawdown_pct: 15\n"
        "max_acceptable_losing_streak: 5\n"
        "daily_loss_limit_usd: 450\n"
        "aggregate_program_drawdown_limit_pct: 20\n"
        "risk_of_ruin_threshold_pct: 5\n\n"
        f'signed_by: "{signers["director_sponsor"]["signer_id"]}"\n'
        f'signed_at_iso: "{signers["director_sponsor"]["signed_at_iso"]}"\n'
        "locked: true\n"
        f'risk_reviewer_countersign_by: "{signers["risk_reviewer"]["signer_id"]}"\n'
        f'risk_reviewer_countersign_at_iso: "{signers["risk_reviewer"]["signed_at_iso"]}"\n'
        'cr_reference: "CR-001"\n'
    )

    current = (
        RISK_LIMITS_PATH.read_text(encoding="utf-8")
        if RISK_LIMITS_PATH.exists()
        else ""
    )
    if 'cr_reference: "CR-001"' in current and "allocated_capital_usd: 5000" in current:
        print("raise-capital: already applied; no change.")
        return 0

    if dry_run:
        print(
            f"[dry-run] OVERWRITE {RISK_LIMITS_PATH.relative_to(REPO_ROOT)} with "
            f"CR-001 §6 values:"
        )
        print(new_yaml)
        return 0

    RISK_LIMITS_PATH.write_text(new_yaml, encoding="utf-8")
    print(f"raise-capital: wrote {RISK_LIMITS_PATH.relative_to(REPO_ROOT)}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CR-001 apply script (registry, signoff matrix, risk limits)."
    )
    parser.add_argument(
        "--step",
        required=True,
        choices=["register-strategies", "raise-capital"],
        help="Which CR-001 step to apply.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended changes without writing.",
    )
    args = parser.parse_args(argv)

    try:
        if args.step == "register-strategies":
            return _step_register_strategies(dry_run=args.dry_run)
        return _step_raise_capital(dry_run=args.dry_run)
    except CrApplyError as exc:
        print(f"CR-001 apply refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
