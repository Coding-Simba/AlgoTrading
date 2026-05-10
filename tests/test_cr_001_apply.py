"""CR-001 apply-script tests: doc + appendices present, signoff block parses,
script refuses without countersigns, skeleton modules importable.
"""

import importlib.util
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_apply_script():
    spec_path = _REPO_ROOT / "tools" / "cr_001_apply.py"
    spec = importlib.util.spec_from_file_location("cr_001_apply", spec_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cr_doc_present() -> None:
    cr_path = _REPO_ROOT / "docs" / "change_requests" / "CR-001_v0.3_v0.4_registration_and_capital.md"
    assert cr_path.exists()


def test_appendices_present() -> None:
    assert (_REPO_ROOT / "docs" / "appendices" / "B_strategy_spec_v0_3.md").exists()
    assert (_REPO_ROOT / "docs" / "appendices" / "B_strategy_spec_v0_4.md").exists()


def test_signoff_block_parses_to_empty_signers() -> None:
    mod = _load_apply_script()
    cr_text = (
        _REPO_ROOT / "docs" / "change_requests" / "CR-001_v0.3_v0.4_registration_and_capital.md"
    ).read_text(encoding="utf-8")
    parsed = mod._read_signoffs(cr_text)
    assert set(parsed.keys()) == {"director_sponsor", "risk_reviewer"}
    assert parsed["director_sponsor"]["signer_id"] == ""
    assert parsed["risk_reviewer"]["signer_id"] == ""


def test_apply_register_strategies_refuses_without_countersigns() -> None:
    mod = _load_apply_script()
    rc = mod.main(["--step", "register-strategies", "--dry-run"])
    assert rc == 2


def test_apply_raise_capital_refuses_without_countersigns() -> None:
    mod = _load_apply_script()
    rc = mod.main(["--step", "raise-capital", "--dry-run"])
    assert rc == 2


def test_skeleton_modules_importable() -> None:
    import algotrading.strategy_v03  # noqa: F401
    import algotrading.strategy_v04  # noqa: F401
    from algotrading.strategy_v04 import classify_regime  # noqa: F401
    from algotrading.strategy_v03 import classify_extension_long  # noqa: F401
