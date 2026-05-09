from __future__ import annotations

from pathlib import Path

import pytest

from algotrading.governance import (
    RiskLimitsError,
    SignoffError,
    assert_risk_limits_signed,
    assert_v02_code_unblocked,
    is_risk_limits_signed,
    load_matrix,
    load_risk_limits,
    require_signed,
)


_PRECODE_TEMPLATE = """\
rows:
  - id: "B"
    title: "Appendix B"
    signer_role: "Director sponsor"
    required_for: "v0.2_code"
    signed: {b_signed}
    signed_by: "{b_by}"
    signed_at_iso: "{b_at}"
    notes: ""
  - id: "C"
    title: "Appendix C"
    signer_role: "Risk reviewer"
    required_for: "v0.2_code"
    signed: {c_signed}
    signed_by: "{c_by}"
    signed_at_iso: "{c_at}"
    notes: ""
  - id: "D"
    title: "Appendix D"
    signer_role: "Engineering"
    required_for: "v0.2_code"
    signed: {d_signed}
    signed_by: "{d_by}"
    signed_at_iso: "{d_at}"
    notes: ""
  - id: "E"
    title: "Appendix E"
    signer_role: "Quant"
    required_for: "v0.2_code"
    signed: {e_signed}
    signed_by: "{e_by}"
    signed_at_iso: "{e_at}"
    notes: ""
  - id: "H"
    title: "Appendix H"
    signer_role: "Engineering"
    required_for: "v0.2_code"
    signed: {h_signed}
    signed_by: "{h_by}"
    signed_at_iso: "{h_at}"
    notes: ""
"""


def _all_signed_kwargs() -> dict[str, str]:
    fields: dict[str, str] = {}
    for letter in ("b", "c", "d", "e", "h"):
        fields[f"{letter}_signed"] = "true"
        fields[f"{letter}_by"] = f"signer_{letter}"
        fields[f"{letter}_at"] = "2026-05-09T10:00:00-04:00"
    return fields


def _none_signed_kwargs() -> dict[str, str]:
    fields: dict[str, str] = {}
    for letter in ("b", "c", "d", "e", "h"):
        fields[f"{letter}_signed"] = "false"
        fields[f"{letter}_by"] = ""
        fields[f"{letter}_at"] = ""
    return fields


def _write_matrix(path: Path, kwargs: dict[str, str]) -> Path:
    path.write_text(_PRECODE_TEMPLATE.format(**kwargs), encoding="utf-8")
    return path


def test_signoff_unsigned_row_blocks_v02_code(tmp_path: Path) -> None:
    p = _write_matrix(tmp_path / "matrix.yml", _none_signed_kwargs())
    with pytest.raises(SignoffError) as exc:
        assert_v02_code_unblocked(p)
    assert "v0.2_code" in str(exc.value)


def test_signoff_partial_signed_blocks_v02_code(tmp_path: Path) -> None:
    kwargs = _all_signed_kwargs()
    kwargs["d_signed"] = "false"
    kwargs["d_by"] = ""
    kwargs["d_at"] = ""
    p = _write_matrix(tmp_path / "matrix.yml", kwargs)
    with pytest.raises(SignoffError) as exc:
        assert_v02_code_unblocked(p)
    assert "'D'" in str(exc.value) or "D" in str(exc.value)


def test_signoff_all_signed_allows_v02_code(tmp_path: Path) -> None:
    p = _write_matrix(tmp_path / "matrix.yml", _all_signed_kwargs())
    assert_v02_code_unblocked(p)


def test_signoff_missing_signer_rejected(tmp_path: Path) -> None:
    kwargs = _all_signed_kwargs()
    kwargs["b_by"] = ""
    p = _write_matrix(tmp_path / "matrix.yml", kwargs)
    with pytest.raises(SignoffError) as exc:
        assert_v02_code_unblocked(p)
    assert "signed_by" in str(exc.value)


def test_signoff_invalid_iso_date_rejected(tmp_path: Path) -> None:
    kwargs = _all_signed_kwargs()
    kwargs["c_at"] = "May 9 2026"
    p = _write_matrix(tmp_path / "matrix.yml", kwargs)
    with pytest.raises(SignoffError) as exc:
        assert_v02_code_unblocked(p)
    assert "signed_at_iso" in str(exc.value)


def test_signoff_unknown_gate_rejected(tmp_path: Path) -> None:
    p = _write_matrix(tmp_path / "matrix.yml", _all_signed_kwargs())
    matrix = load_matrix(p)
    with pytest.raises(SignoffError):
        require_signed(matrix, gate="not_a_gate")


def test_signoff_missing_file_rejected(tmp_path: Path) -> None:
    with pytest.raises(SignoffError):
        assert_v02_code_unblocked(tmp_path / "missing.yml")


def test_signoff_duplicate_row_id_rejected(tmp_path: Path) -> None:
    p = tmp_path / "dup.yml"
    p.write_text(
        "rows:\n"
        "  - id: 'B'\n    title: 't'\n    signer_role: 'r'\n"
        "    required_for: 'v0.2_code'\n    signed: false\n"
        "    signed_by: ''\n    signed_at_iso: ''\n    notes: ''\n"
        "  - id: 'B'\n    title: 't'\n    signer_role: 'r'\n"
        "    required_for: 'v0.2_code'\n    signed: false\n"
        "    signed_by: ''\n    signed_at_iso: ''\n    notes: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(SignoffError) as exc:
        load_matrix(p)
    assert "duplicate" in str(exc.value).lower()


_RISK_TEMPLATE = """\
allocated_capital_usd: {capital}
max_oos_drawdown_pct: {oos_dd}
max_acceptable_losing_streak: {streak}
daily_loss_limit_usd: {daily}
aggregate_program_drawdown_limit_pct: {agg_dd}
risk_of_ruin_threshold_pct: {ror}
signed_by: "{signed_by}"
signed_at_iso: "{signed_at}"
locked: {locked}
"""


def _risk_complete_kwargs() -> dict[str, str]:
    return dict(
        capital="100000",
        oos_dd="20",
        streak="6",
        daily="2000",
        agg_dd="25",
        ror="5",
        signed_by="director",
        signed_at="2026-05-09T10:00:00-04:00",
        locked="true",
    )


def _write_risk(path: Path, kwargs: dict[str, str]) -> Path:
    path.write_text(_RISK_TEMPLATE.format(**kwargs), encoding="utf-8")
    return path


def test_risk_limits_unsigned_blocks(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["locked"] = "false"
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    assert not is_risk_limits_signed(p)
    with pytest.raises(RiskLimitsError):
        assert_risk_limits_signed(p)


def test_risk_limits_partial_values_block(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["streak"] = ""
    kwargs["daily"] = ""
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    assert not is_risk_limits_signed(p)
    with pytest.raises(RiskLimitsError) as exc:
        assert_risk_limits_signed(p)
    msg = str(exc.value)
    assert "max_acceptable_losing_streak" in msg
    assert "daily_loss_limit_usd" in msg


def test_risk_limits_negative_capital_blocks(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["capital"] = "-1"
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    with pytest.raises(RiskLimitsError) as exc:
        assert_risk_limits_signed(p)
    assert "allocated_capital_usd" in str(exc.value)


def test_risk_limits_drawdown_out_of_range_blocks(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["oos_dd"] = "150"
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    with pytest.raises(RiskLimitsError) as exc:
        assert_risk_limits_signed(p)
    assert "max_oos_drawdown_pct" in str(exc.value)


def test_risk_limits_zero_losing_streak_blocks(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["streak"] = "0"
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    with pytest.raises(RiskLimitsError) as exc:
        assert_risk_limits_signed(p)
    assert "max_acceptable_losing_streak" in str(exc.value)


def test_risk_limits_bad_signer_blocks(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["signed_by"] = ""
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    with pytest.raises(RiskLimitsError) as exc:
        assert_risk_limits_signed(p)
    assert "signed_by" in str(exc.value)


def test_risk_limits_bad_iso_date_blocks(tmp_path: Path) -> None:
    kwargs = _risk_complete_kwargs()
    kwargs["signed_at"] = "yesterday"
    p = _write_risk(tmp_path / "risk.yml", kwargs)
    with pytest.raises(RiskLimitsError) as exc:
        assert_risk_limits_signed(p)
    assert "signed_at_iso" in str(exc.value)


def test_risk_limits_complete_and_signed_allows(tmp_path: Path) -> None:
    p = _write_risk(tmp_path / "risk.yml", _risk_complete_kwargs())
    assert is_risk_limits_signed(p)
    assert_risk_limits_signed(p)
    limits = load_risk_limits(p)
    assert limits.allocated_capital_usd == 100000.0
    assert limits.max_acceptable_losing_streak == 6
    assert limits.locked is True


def test_risk_limits_missing_file_blocks(tmp_path: Path) -> None:
    missing = tmp_path / "absent.yml"
    assert not is_risk_limits_signed(missing)
    with pytest.raises(RiskLimitsError):
        assert_risk_limits_signed(missing)
