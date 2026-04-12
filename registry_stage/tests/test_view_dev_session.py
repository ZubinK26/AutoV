"""G8 — read-only DevSessionSnapshot viewers."""

from __future__ import annotations

import json

from registry_stage.view_dev_session import write_dev_session_views


def _minimal_snapshot() -> dict:
    return {
        "schema_version": "registry_persistence_v1",
        "dev_export": True,
        "bundle_id": "test_bu",
        "notes": "",
        "handoff": {
            "bundle_id": "test_bu",
            "user_original_input": "Hello world",
            "lines": [{"line_index": 0, "statement_nl": "Rule one.", "agent3_verdict": "PASS"}],
        },
        "registry": {"schema_version": "registry_persistence_v1", "entries": [], "entry_edges": []},
        "line_traces": [
            {
                "bundle_id": "test_bu",
                "line_index": 0,
                "statement_nl": "Rule one.",
                "agent3_verdict": "PASS",
                "hits": [{"entry_id": "ent_a", "score": 0.5}],
                "authoritative_hits": [{"entry_id": "ent_a", "score": 0.9}],
                "gap_spans": ["Acme"],
                "structured_gaps": [],
                "raw_structured_gaps": [],
                "expansion_phrases": ["x"],
                "search_queries_used": ["q1"],
                "authoritative_min_score": 0.2,
                "semantic_backend_label": "stub",
                "pre_resolved_nl": None,
                "registry_resolution_candidate_nl": "cand",
                "registry_resolved_nl": "final",
                "resolve_mode": "auto",
                "validation_outcome": "ok",
                "failure_reasons": [],
                "new_entry_ids": ["ent_new_1"],
                "raw_resolver_json": [{"schema_version": "resolve_v1"}],
                "attempts_used": 1,
                "llm_rationale_short": "r",
            }
        ],
    }


def test_write_dev_session_views_creates_stage_folders(tmp_path) -> None:
    snap = _minimal_snapshot()
    out = tmp_path / "v"
    write_dev_session_views(snap, out)
    assert (out / "index.md").is_file()
    assert (out / "handoff_overview.md").is_file()
    assert (out / "registry_summary.md").is_file()
    assert (out / "01_search" / "line_00.md").is_file()
    assert (out / "04_populate" / "line_00.md").is_file()
    idx = (out / "index.md").read_text(encoding="utf-8")
    assert "01_search" in idx
    search_md = (out / "01_search" / "line_00.md").read_text(encoding="utf-8")
    assert "Search" in search_md
    assert "ent_a" in search_md
    pop_md = (out / "04_populate" / "line_00.md").read_text(encoding="utf-8")
    assert "ent_new_1" in pop_md


def test_empty_line_traces_still_writes_index(tmp_path) -> None:
    snap = {
        "schema_version": "registry_persistence_v1",
        "dev_export": True,
        "bundle_id": "x",
        "handoff": None,
        "registry": {"schema_version": "registry_persistence_v1", "entries": [], "entry_edges": []},
        "line_traces": [],
    }
    write_dev_session_views(snap, tmp_path / "v")
    idx = (tmp_path / "v" / "index.md").read_text(encoding="utf-8")
    assert "no `line_traces`" in idx


def test_cli_module_loads_json(tmp_path) -> None:
    p = tmp_path / "s.json"
    p.write_text(json.dumps(_minimal_snapshot()), encoding="utf-8")
    from registry_stage.view_dev_session import main

    assert main(["-i", str(p), "-o", str(tmp_path / "out")]) == 0
    assert (tmp_path / "out" / "index.md").is_file()
