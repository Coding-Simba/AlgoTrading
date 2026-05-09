"""Command-line interface for the local trading application.

Sub-commands:

    gates check                            # show every gate's state
    strategy-v02 unit-check                # quick smoke of strategy rules
    run synthetic                          # synthetic E2E
    run training --config <path>           # training runner
    paper simulate --synthetic             # paper simulator on synthetic
    report generate --synthetic            # generate a synthetic report
    live status                            # live adapter gate status
    live enable                            # attempt to enable live (always BLOCKED)
    scale status                           # scale-up gate status

Every command refuses to do dangerous work and exits non-zero with a
``BLOCKED_*`` reason if the relevant gate is not satisfied.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _cmd_gates_check(_args: argparse.Namespace) -> int:
    from .governance.phase_gates import GateContext, gate_summary

    ctx = GateContext.default(_repo_root())
    summary = gate_summary(ctx)
    print(json.dumps(summary, indent=2, default=str))
    return 0


def _cmd_strategy_v02_unit_check(_args: argparse.Namespace) -> int:
    from .indicators import ema, wilder_atr, session_vwap
    from .strategy_v02 import EntrySide, round_to_tick

    closes = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]
    e = ema(closes, period=5)
    a = wilder_atr(
        highs=[c + 1 for c in closes],
        lows=[c - 1 for c in closes],
        closes=closes,
        period=5,
    )
    v = session_vwap(closes, [1] * len(closes), [0])
    long_target = round_to_tick(100.7, EntrySide.LONG)
    short_target = round_to_tick(100.3, EntrySide.SHORT)

    print(json.dumps(
        {
            "ema_last": e[-1],
            "atr_last": a[-1],
            "vwap_last": v[-1],
            "long_round_to_tick(100.7)": long_target,
            "short_round_to_tick(100.3)": short_target,
        },
        indent=2,
    ))
    return 0


def _cmd_run_synthetic(_args: argparse.Namespace) -> int:
    from .paper.simulator import PaperSimulator, synthetic_bars
    from .reporting import generate_run_report

    sim = PaperSimulator()
    res = sim.run(synthetic_bars(60))
    rep = generate_run_report(res, title="v0.2 synthetic E2E")
    print(rep.render())
    return 0


def _cmd_run_training(args: argparse.Namespace) -> int:
    import yaml
    from .paper.simulator import synthetic_bars
    from .research import TrainingRunner

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"BLOCKED_TRAINING: config not found: {cfg_path}", file=sys.stderr)
        return 2
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    mode = str(cfg.get("mode") or "synthetic")
    n = int(cfg.get("synthetic_bars") or 60)
    runner = TrainingRunner(_repo_root())
    if mode == "synthetic":
        result = runner.run_synthetic(synthetic_bars(n))
        print(json.dumps(
            {
                "mode": result.mode,
                "approved": result.backtest.approved,
                "placeholder_costs_present": result.backtest.placeholder_cost_tag_present,
                "bars_processed": result.backtest.paper_result.bars_processed,
                "entries_taken": result.backtest.paper_result.entries_taken,
                "fills": result.backtest.paper_result.fills,
            },
            indent=2,
        ))
        return 0
    try:
        result = runner.run_real(synthetic_bars(n))
    except Exception as exc:  # noqa: BLE001
        print(f"BLOCKED_TRAINING: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"mode": result.mode}, indent=2))
    return 0


def _cmd_paper_simulate(args: argparse.Namespace) -> int:
    if not args.synthetic:
        print(
            "BLOCKED_PAPER: only --synthetic is implemented in v0.2; real "
            "paper sessions require Appendix F finalization.",
            file=sys.stderr,
        )
        return 4
    return _cmd_run_synthetic(args)


def _cmd_report_generate(args: argparse.Namespace) -> int:
    if not args.synthetic:
        print(
            "BLOCKED_REPORT: only --synthetic is implemented in v0.2.",
            file=sys.stderr,
        )
        return 5
    from .paper.simulator import PaperSimulator, synthetic_bars
    from .reporting import generate_run_report

    sim = PaperSimulator()
    res = sim.run(synthetic_bars(60))
    rep = generate_run_report(res, title="v0.2 synthetic report")
    print(rep.render())
    return 0


def _cmd_live_status(_args: argparse.Namespace) -> int:
    from .broker import BlockedLiveTrading, LiveBrokerAdapter

    adapter = LiveBrokerAdapter(repo_root=_repo_root())
    try:
        adapter._gate()  # noqa: SLF001
    except BlockedLiveTrading as exc:
        print(json.dumps({"live": "BLOCKED", "reason": str(exc)}, indent=2))
        return 0
    print(json.dumps({"live": "ALLOWED", "reason": None}, indent=2))
    return 0


def _cmd_live_enable(_args: argparse.Namespace) -> int:
    from .broker import BlockedLiveTrading, LiveBrokerAdapter
    from .broker.interface import BrokerOrder

    adapter = LiveBrokerAdapter(repo_root=_repo_root())
    try:
        adapter.submit(
            BrokerOrder(
                client_order_id="V02-ENABLE-PROBE",
                symbol="MES",
                side="buy",
                qty=1,
                order_type="market",
                price=None,
            )
        )
    except BlockedLiveTrading as exc:
        print(f"BLOCKED_LIVE_TRADING: {exc}", file=sys.stderr)
        return 1
    print("ENABLED (no real order placed; live path is a v0.2 stub)")
    return 0


def _cmd_scale_status(_args: argparse.Namespace) -> int:
    from .governance.phase_gates import (
        GateBlocked,
        GateContext,
        assert_scaleup_unblocked,
    )

    ctx = GateContext.default(_repo_root())
    try:
        assert_scaleup_unblocked(ctx)
    except GateBlocked as exc:
        print(json.dumps({"scale": "BLOCKED", "reason": str(exc)}, indent=2))
        return 0
    print(json.dumps({"scale": "ALLOWED", "reason": None}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="algotrading", description="v0.2 trading app")
    sub = p.add_subparsers(dest="cmd", required=True)

    gates = sub.add_parser("gates", help="gate inspection")
    gates_sub = gates.add_subparsers(dest="gates_cmd", required=True)
    gates_check = gates_sub.add_parser("check", help="show every gate's state")
    gates_check.set_defaults(func=_cmd_gates_check)

    strat = sub.add_parser("strategy-v02", help="strategy v0.2 utilities")
    strat_sub = strat.add_subparsers(dest="strat_cmd", required=True)
    strat_unit = strat_sub.add_parser("unit-check", help="strategy unit smoke")
    strat_unit.set_defaults(func=_cmd_strategy_v02_unit_check)

    run = sub.add_parser("run", help="run a path")
    run_sub = run.add_subparsers(dest="run_cmd", required=True)
    run_syn = run_sub.add_parser("synthetic", help="synthetic E2E")
    run_syn.set_defaults(func=_cmd_run_synthetic)
    run_train = run_sub.add_parser("training", help="training runner")
    run_train.add_argument("--config", required=True)
    run_train.set_defaults(func=_cmd_run_training)

    paper = sub.add_parser("paper", help="paper sim")
    paper_sub = paper.add_subparsers(dest="paper_cmd", required=True)
    paper_sim = paper_sub.add_parser("simulate", help="run paper simulator")
    paper_sim.add_argument("--synthetic", action="store_true")
    paper_sim.set_defaults(func=_cmd_paper_simulate)

    report = sub.add_parser("report", help="reporting")
    report_sub = report.add_subparsers(dest="report_cmd", required=True)
    report_gen = report_sub.add_parser("generate", help="generate run report")
    report_gen.add_argument("--synthetic", action="store_true")
    report_gen.set_defaults(func=_cmd_report_generate)

    live = sub.add_parser("live", help="live adapter (refuses by default)")
    live_sub = live.add_subparsers(dest="live_cmd", required=True)
    live_status = live_sub.add_parser("status", help="live gate status")
    live_status.set_defaults(func=_cmd_live_status)
    live_enable = live_sub.add_parser("enable", help="attempt to enable live (BLOCKED)")
    live_enable.set_defaults(func=_cmd_live_enable)

    scale = sub.add_parser("scale", help="scale-up status")
    scale_sub = scale.add_subparsers(dest="scale_cmd", required=True)
    scale_status = scale_sub.add_parser("status", help="scale-up gate status")
    scale_status.set_defaults(func=_cmd_scale_status)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
