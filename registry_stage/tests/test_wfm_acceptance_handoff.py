"""G1 — acceptance snapshot → HandoffBundle → validate → optional registry run."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from registry_stage.bundle_workflow import run_bundle_through_registry
from registry_stage.line_driver import LineDriverConfig
from registry_stage.loaders import load_handoff_bundle
from registry_stage.models import SCHEMA_VERSION, HandoffBundle, HandoffLine
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex
from registry_stage.wfm_acceptance_handoff import (
    WfmAcceptanceLine,
    WfmAcceptanceSnapshot,
    acceptance_snapshot_from_jsonable,
    build_handoff_bundle,
    load_acceptance_snapshot,
    validate_handoff_roundtrip,
    write_handoff_bundle,
)

REGISTRY_STAGE = Path(__file__).resolve().parents[1]
REPO_ROOT = REGISTRY_STAGE.parent
FIXTURE_BUNDLE = REPO_ROOT / "bundles" / "fixture_bu_001.json"


def test_build_handoff_from_snapshot_matches_constructed_bundle() -> None:
    snap = WfmAcceptanceSnapshot(
        bundle_id="bu_test",
        user_original_input="hello",
        lines=(
            WfmAcceptanceLine(0, "Line zero.", "PASS", agent2_line_text='1. "Line zero."'),
            WfmAcceptanceLine(1, "Line one OOS.", "OUT_OF_SCOPE", scope_report="too hard"),
        ),
        wfm_pipeline_timestamps={"confirmation_accepted_utc": "2026-01-01T00:00:00Z"},
        provider_model="gemini-test",
        wfm_compound_operator_limit=8,
    )
    built = build_handoff_bundle(snap)
    direct = HandoffBundle(
        schema_version=SCHEMA_VERSION,
        bundle_id="bu_test",
        user_original_input="hello",
        lines=[
            HandoffLine(0, "Line zero.", "PASS", None, None, '1. "Line zero."'),
            HandoffLine(1, "Line one OOS.", "OUT_OF_SCOPE", "too hard", None, None),
        ],
        confirmation_package_style_a=None,
        orchestration_run_id=None,
        wfm_pipeline_timestamps={"confirmation_accepted_utc": "2026-01-01T00:00:00Z"},
        provider_model="gemini-test",
        wfm_compound_operator_limit=8,
    )
    assert built == direct


def test_validate_handoff_roundtrip_fixture_file() -> None:
    bundle = load_handoff_bundle(FIXTURE_BUNDLE)
    again = validate_handoff_roundtrip(bundle)
    assert again.bundle_id == bundle.bundle_id
    assert len(again.lines) == len(bundle.lines)


def test_acceptance_snapshot_from_fixture_json() -> None:
    raw = json.loads(FIXTURE_BUNDLE.read_text(encoding="utf-8"))
    snap = acceptance_snapshot_from_jsonable(raw)
    built = build_handoff_bundle(snap)
    from_disk = load_handoff_bundle(FIXTURE_BUNDLE)
    assert built == from_disk


def test_duplicate_line_index_raises() -> None:
    with pytest.raises(ValueError, match="duplicate line_index"):
        WfmAcceptanceSnapshot(
            bundle_id="x",
            user_original_input="u",
            lines=(
                WfmAcceptanceLine(0, "a", "PASS"),
                WfmAcceptanceLine(0, "b", "PASS"),
            ),
        )


def test_bad_verdict_raises() -> None:
    with pytest.raises(ValueError, match="agent3_verdict"):
        WfmAcceptanceLine(0, "a", "INVALID")


def test_write_handoff_roundtrip_tmp_path(tmp_path: Path) -> None:
    snap = WfmAcceptanceSnapshot(
        bundle_id="bu_tmp",
        user_original_input="u",
        lines=(WfmAcceptanceLine(0, "One.", "PASS"),),
    )
    bundle = build_handoff_bundle(snap)
    out = tmp_path / "out.json"
    write_handoff_bundle(out, bundle)
    loaded = load_handoff_bundle(out)
    assert validate_handoff_roundtrip(loaded).bundle_id == "bu_tmp"


def test_load_acceptance_snapshot_writes_via_builder(tmp_path: Path) -> None:
    """Acceptance snapshot file (no schema_version required) → bundle file."""
    p = tmp_path / "accept.json"
    p.write_text(
        json.dumps(
            {
                "bundle_id": "snap1",
                "user_original_input": "raw",
                "lines": [{"line_index": 0, "statement_nl": "S.", "agent3_verdict": "PASS"}],
            }
        ),
        encoding="utf-8",
    )
    snap = load_acceptance_snapshot(p)
    bundle = build_handoff_bundle(snap)
    assert bundle.lines[0].statement_nl == "S."


def test_run_bundle_from_built_handoff_stub_llm() -> None:
    snap = WfmAcceptanceSnapshot(
        bundle_id="bu_g1",
        user_original_input="u",
        lines=(WfmAcceptanceLine(0, "Northwind test line for stub.", "PASS"),),
    )
    bundle = validate_handoff_roundtrip(build_handoff_bundle(snap))
    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")

    def llm_complete(_system: str, _user: str) -> str:
        return json.dumps(
            {
                "schema_version": "resolve_v1",
                "registry_resolution_candidate_nl": "resolved ok",
                "cited_entry_ids": [],
                "needs_human_review": False,
                "primary_review_reason": "NONE",
                "confidence_tier": "high",
                "llm_rationale_short": "ok",
            }
        )

    cfg = LineDriverConfig(enable_llm=True, llm_complete=llm_complete)
    snap_out = run_bundle_through_registry(
        bundle, session, llm_complete=llm_complete, line_config=cfg
    )
    assert snap_out.bundle is not None
    assert snap_out.bundle.bundle_id == "bu_g1"
    assert len(snap_out.line_traces) == 1
