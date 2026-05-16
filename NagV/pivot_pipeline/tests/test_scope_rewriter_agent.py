"""Tests for pre-WFM Scope Rewriter (no live Gemini)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pivot_pipeline.scope_rewriter_agent import (
    INPUT_MODE_POLICY_INTENT_SPEC,
    INPUT_MODE_REFERENCE_CORPUS,
    SCHEMA_VERSION,
    build_user_initial,
    extract_json_object,
    normalize_input_mode,
    normalize_plain_rules,
    parse_llm_output,
    run_scope_rewriter_round,
)


def test_normalize_input_mode_explicit_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_input_mode("bogus")


def test_build_user_initial_policy_spec_header() -> None:
    u = build_user_initial(reference_text="Spec line.", input_mode=INPUT_MODE_POLICY_INTENT_SPEC)
    assert "## Scope Rewriter input_mode" in u
    assert INPUT_MODE_POLICY_INTENT_SPEC in u
    assert "Policy intent specification" in u


def test_build_user_initial_reference_mode_header() -> None:
    u = build_user_initial(reference_text="Rule.", input_mode=INPUT_MODE_REFERENCE_CORPUS)
    assert INPUT_MODE_REFERENCE_CORPUS in u
    assert "Reference document" in u


def test_parse_llm_output_coerces_none_string_dropped_facets() -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plain_rules": "One.",
        "fidelity_summary": "ok",
        "strict_equivalence_achievable": True,
        "partial_rewrites": [],
        "semantic_deltas": [],
        "ready_for_wfm": True,
        "no_further_agent_changes_recommended": False,
        "enumerations_compressed": [
            {"topic": "t", "kept": "k", "dropped_facets": "None"},
        ],
    }
    p = parse_llm_output(json.dumps(payload))
    assert p.enumerations_compressed[0].dropped_facets == []


def test_normalize_plain_rules() -> None:
    assert normalize_plain_rules("  a \n\n b ") == "a\nb\n"


def test_extract_json_object_fenced() -> None:
    raw = """Here is JSON:
```json
{"a": 1, "b": "x"}
```
"""
    assert extract_json_object(raw) == {"a": 1, "b": "x"}


def test_parse_llm_output_full() -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plain_rules": "Rule one.\nRule two.",
        "fidelity_summary": "ok",
        "strict_equivalence_achievable": True,
        "partial_rewrites": [],
        "semantic_deltas": ["assumed X"],
        "ready_for_wfm": True,
        "no_further_agent_changes_recommended": False,
    }
    p = parse_llm_output(json.dumps(payload))
    assert p.plain_rules.count("\n") == 1
    assert p.modality_notes == []
    assert p.line_encodability_tags == []


def test_parse_llm_output_extended_sidecar() -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "plain_rules": "A.\nB.",
        "fidelity_summary": "extended",
        "strict_equivalence_achievable": False,
        "partial_rewrites": [
            {
                "approximate_line_span": "task list",
                "reason": "compressed",
                "nearest_rewrite_note": "see semantic_deltas",
            }
        ],
        "semantic_deltas": ["weakened iff"],
        "ready_for_wfm": False,
        "no_further_agent_changes_recommended": False,
        "modality_notes": ["Source iff X; output only-if."],
        "omissions_check": ["Blocks represented: intro, tasks."],
        "enumerations_compressed": [
            {
                "topic": "checks",
                "kept": "A and B",
                "dropped_facets": ["C"],
            }
        ],
        "line_encodability_tags": ["state_constraint", "temporal_or_process_order"],
        "high_friction_line_indices": [2],
        "suggested_human_review_focus": ["branch naming"],
    }
    p = parse_llm_output(json.dumps(payload))
    assert p.enumerations_compressed[0].topic == "checks"
    assert p.enumerations_compressed[0].dropped_facets == ["C"]
    assert p.line_encodability_tags == [
        "state_constraint",
        "temporal_or_process_order",
    ]
    assert p.high_friction_line_indices == [2]


def test_parse_llm_output_missing_field() -> None:
    with pytest.raises(Exception):
        parse_llm_output(json.dumps({"schema_version": SCHEMA_VERSION}))


def test_run_scope_rewriter_round_writes_files(tmp_path: Path) -> None:
    ref = tmp_path / "ref.md"
    ref.write_text("# Ref\n\nMust do A.\n", encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()

    def fake_llm(_si: str, _ut: str) -> str:
        return json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "plain_rules": "Must do A.",
                "fidelity_summary": "test",
                "strict_equivalence_achievable": True,
                "partial_rewrites": [],
                "semantic_deltas": [],
                "ready_for_wfm": True,
                "no_further_agent_changes_recommended": True,
                "modality_notes": [],
                "line_encodability_tags": ["state_constraint"],
                "high_friction_line_indices": [],
                "suggested_human_review_focus": [],
            },
            ensure_ascii=False,
        )

    r = run_scope_rewriter_round(
        reference_path=ref,
        work_dir=work,
        round_index=0,
        prior_nl_path=None,
        prior_sidecar=None,
        operator_note="",
        system_instruction="SYS",
        input_mode=INPUT_MODE_POLICY_INTENT_SPEC,
        llm_fn=fake_llm,
    )
    assert r.nl_path.is_file()
    assert r.sidecar_path.is_file()
    body = r.nl_path.read_text(encoding="utf-8")
    assert "Must do A" in body
    data = json.loads(r.sidecar_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["input_mode"] == INPUT_MODE_POLICY_INTENT_SPEC
    assert "reference_sha256" in data
    assert data["line_encodability_tags"] == ["state_constraint"]
    assert "modality_notes" in data
    assert "enumerations_compressed" in data


def test_scope_rewriter_prompt_exists() -> None:
    p = _REPO / "NagV" / "pivot_pipeline" / "prompts" / "scope_rewriter_pre_wfm.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "plain_rules" in text
    assert "line_encodability_tags" in text
    assert "policy_intent_spec" in text
    assert "Scope Rewriter input_mode" in text


def test_load_system_prompt_contains_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    import pivot_pipeline.scope_rewriter_agent as sra

    monkeypatch.setattr(sra, "read_v1_policy_encodability_contract", lambda: "CONTRACT_STUB")
    txt = sra.load_scope_rewriter_system_prompt()
    assert "CONTRACT_STUB" in txt
    assert "Scope Rewriter" in txt
