"""M0: imports and fixture presence only."""

from pathlib import Path

import pytest

import registry_stage


def test_package_imports() -> None:
    assert registry_stage.__version__ == "0.0.m3"


def test_fixture_handoff_exists_and_minimal_shape() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "bundles" / "fixture_bu_001.json"
    assert path.is_file(), f"Missing {path}"

    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("schema_version") == "registry_persistence_v1"
    assert data.get("bundle_id") == "fixture_bu_001"
    lines = data.get("lines")
    assert isinstance(lines, list) and len(lines) >= 2

    verdicts = {ln.get("agent3_verdict") for ln in lines}
    assert "PASS" in verdicts
    assert "OUT_OF_SCOPE" in verdicts

    for ln in lines:
        assert "line_index" in ln and "statement_nl" in ln
        assert ln["agent3_verdict"] in ("PASS", "REWRITE", "OUT_OF_SCOPE")
