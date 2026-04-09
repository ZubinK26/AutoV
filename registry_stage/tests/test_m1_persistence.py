"""M1: load handoff + registry, validation stub, dev export."""

from __future__ import annotations

import json
from pathlib import Path

import registry_stage
from registry_stage.export_session import export_session
from registry_stage.loaders import load_handoff_bundle, load_registry
from registry_stage.models import DevSessionSnapshot, SCHEMA_VERSION
from registry_stage.validation import validate_alignment


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_m1_version() -> None:
    assert registry_stage.__version__ == "0.0.m5"


def test_load_fixture_handoff_and_empty_registry_no_crash(tmp_path: Path) -> None:
    root = _repo_root()
    bundle_path = root / "bundles" / "fixture_bu_001.json"
    bundle = load_handoff_bundle(bundle_path)
    assert bundle.bundle_id == "fixture_bu_001"
    assert len(bundle.lines) == 3
    assert bundle.lines[0].line_index == 0
    assert bundle.lines[2].agent3_verdict == "OUT_OF_SCOPE"

    reg_path = tmp_path / "registry.json"
    reg_path.write_text(
        json.dumps(
            {"schema_version": SCHEMA_VERSION, "entries": [], "entry_edges": []},
            indent=2,
        ),
        encoding="utf-8",
    )
    reg = load_registry(reg_path)
    assert reg.schema_version == SCHEMA_VERSION
    assert reg.entries == []
    assert reg.entry_edges == []


def test_load_registry_missing_file_is_empty_shell() -> None:
    reg = load_registry(Path("/nonexistent/path/registry.json"))
    assert reg.entries == []
    assert reg.entry_edges == []
    assert reg.schema_version == SCHEMA_VERSION


def test_validate_alignment_stub_returns_empty() -> None:
    reg = load_registry(Path("/missing/registry.json"))
    assert validate_alignment(reg) == []
    assert validate_alignment(reg, rule_rows=[]) == []


def test_export_session_dev_flag_and_roundtrip_keys(tmp_path: Path) -> None:
    root = _repo_root()
    bundle = load_handoff_bundle(root / "bundles" / "fixture_bu_001.json")
    reg = load_registry(tmp_path / "none.json")
    snap = DevSessionSnapshot(registry=reg, bundle=bundle, notes="m1 test")
    out = tmp_path / "dev_session.json"
    export_session(out, snap)

    raw = json.loads(out.read_text(encoding="utf-8"))
    assert raw.get("dev_export") is True
    assert raw.get("schema_version") == SCHEMA_VERSION
    assert raw.get("bundle_id") == "fixture_bu_001"
    assert raw.get("notes") == "m1 test"
    assert raw.get("handoff") is not None
    assert raw["handoff"]["bundle_id"] == "fixture_bu_001"
    assert raw.get("registry") == {
        "schema_version": SCHEMA_VERSION,
        "entries": [],
        "entry_edges": [],
    }
