from pathlib import Path

import pytest

from algotrading.registry import RegistryError, StrategyRegistry


def test_append_and_read(tmp_path: Path) -> None:
    reg = StrategyRegistry(tmp_path / "reg.jsonl")
    e1 = reg.append(
        strategy_version="v0.2",
        family="MES_intraday",
        rules={"entry": "B.7", "ema": 21},
        registered_by="j_smith",
    )
    e2 = reg.append(
        strategy_version="v0.2",
        family="MES_intraday",
        rules={"entry": "B.8"},
        registered_by="j_smith",
    )
    assert e1.entry_id != e2.entry_id
    entries = reg.entries()
    assert len(entries) == 2
    assert reg.latest_for_version("v0.2").entry_id == e2.entry_id
    assert reg.find_by_id(e1.entry_id) == e1


def test_supersedes_must_reference_known_id(tmp_path: Path) -> None:
    reg = StrategyRegistry(tmp_path / "reg.jsonl")
    with pytest.raises(RegistryError):
        reg.append(
            strategy_version="v0.2",
            family="MES_intraday",
            rules={"entry": "B.7"},
            registered_by="j_smith",
            supersedes="nonexistent",
        )


def test_validate_clean(tmp_path: Path) -> None:
    reg = StrategyRegistry(tmp_path / "reg.jsonl")
    reg.append(
        strategy_version="v0.2",
        family="MES_intraday",
        rules={"entry": "B.7"},
        registered_by="j_smith",
    )
    assert reg.validate() == []


def test_rules_hash_change_detected(tmp_path: Path) -> None:
    path = tmp_path / "reg.jsonl"
    reg = StrategyRegistry(path)
    reg.append(
        strategy_version="v0.2",
        family="MES_intraday",
        rules={"entry": "B.7"},
        registered_by="j_smith",
    )
    line = path.read_text().strip()
    tampered = line.replace('"B.7"', '"B.8"')
    path.write_text(tampered + "\n")
    reg2 = StrategyRegistry(path)
    errs = reg2.validate()
    assert any("rules_hash mismatch" in e for e in errs)


def test_required_fields(tmp_path: Path) -> None:
    reg = StrategyRegistry(tmp_path / "reg.jsonl")
    with pytest.raises(RegistryError):
        reg.append(strategy_version="", family="f", rules={"a": 1}, registered_by="x")
    with pytest.raises(RegistryError):
        reg.append(strategy_version="v0.2", family="", rules={"a": 1}, registered_by="x")
    with pytest.raises(RegistryError):
        reg.append(strategy_version="v0.2", family="f", rules={}, registered_by="x")
    with pytest.raises(RegistryError):
        reg.append(strategy_version="v0.2", family="f", rules={"a": 1}, registered_by="")
