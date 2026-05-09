"""CLI smoke tests."""

import json


from algotrading.cli import build_parser, main


def test_cli_parser_has_all_required_subcommands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for token in (
        "gates",
        "strategy-v02",
        "run",
        "paper",
        "report",
        "live",
        "scale",
    ):
        assert token in help_text


def test_cli_gates_check_runs_and_emits_blocked_for_v02_code(capsys) -> None:
    code = main(["gates", "check"])
    assert code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["v0.2_code"]["status"] == "BLOCKED"
    assert parsed["live"]["status"] == "BLOCKED"
    assert parsed["scaleup"]["status"] == "BLOCKED"


def test_cli_strategy_unit_check_runs(capsys) -> None:
    code = main(["strategy-v02", "unit-check"])
    assert code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "ema_last" in parsed
    assert parsed["long_round_to_tick(100.7)"] == 100
    assert parsed["short_round_to_tick(100.3)"] == 101


def test_cli_run_synthetic_renders_report(capsys) -> None:
    code = main(["run", "synthetic"])
    assert code == 0
    out = capsys.readouterr().out
    assert "approved: False" in out


def test_cli_paper_simulate_synthetic_runs(capsys) -> None:
    code = main(["paper", "simulate", "--synthetic"])
    assert code == 0
    out = capsys.readouterr().out
    assert "bars_processed" in out


def test_cli_report_generate_synthetic(capsys) -> None:
    code = main(["report", "generate", "--synthetic"])
    assert code == 0
    out = capsys.readouterr().out
    assert "approved: False" in out


def test_cli_live_status_reports_blocked(capsys) -> None:
    code = main(["live", "status"])
    assert code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["live"] == "BLOCKED"


def test_cli_live_enable_blocked(capsys) -> None:
    code = main(["live", "enable"])
    assert code != 0
    err = capsys.readouterr().err
    assert "BLOCKED_LIVE_TRADING" in err


def test_cli_scale_status_blocked(capsys) -> None:
    code = main(["scale", "status"])
    assert code == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["scale"] == "BLOCKED"
