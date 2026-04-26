"""Resume logic and batch orchestration for SymTex WFM (no live Gemini)."""

from __future__ import annotations

import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from registry_stage.models import DevSessionSnapshot, HandoffBundle, HandoffLine

from wfm_orchestration.asp_demo_sources import SymTexPairedExample
from wfm_orchestration.run_symtex_wfm_batch import (
    append_completed,
    completed_jsonl_path,
    load_completed_keys,
    pending_examples,
    run_symtex_batch,
    symtex_example_key,
)


def _ex(task: str, sid: str) -> SymTexPairedExample:
    return SymTexPairedExample(
        task=task,  # type: ignore[arg-type]
        source_id=sid,
        nl_document=f"nl-{sid}",
        reference_asp_program=f"asp-{sid}",
        textual_jsonl_relpath="t.jsonl",
        symbolic_jsonl_relpath="s.jsonl",
        extra={},
    )


def test_load_append_completed_roundtrip(tmp_path: Path) -> None:
    p = completed_jsonl_path(tmp_path)
    assert load_completed_keys(p) == set()
    append_completed(
        p,
        {"success": True, "example_key": "answerset_generation:a", "bundle_id": "b1"},
    )
    assert load_completed_keys(p) == {"answerset_generation:a"}
    append_completed(
        p,
        {"success": True, "example_key": "fact_state_querying:b", "bundle_id": "b2"},
    )
    assert load_completed_keys(p) == {"answerset_generation:a", "fact_state_querying:b"}


def test_pending_examples_filters_completed() -> None:
    idx = [_ex("answerset_generation", "1"), _ex("answerset_generation", "2")]
    done = {symtex_example_key(idx[0])}
    pend = pending_examples(idx, done)
    assert len(pend) == 1
    assert pend[0].source_id == "2"


def test_run_symtex_batch_resume_skips_completed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    idx = [_ex("answerset_generation", "done"), _ex("answerset_generation", "two"), _ex("answerset_generation", "three")]
    cpath = completed_jsonl_path(tmp_path)
    append_completed(
        cpath,
        {
            "success": True,
            "example_key": symtex_example_key(idx[0]),
            "bundle_id": "old",
        },
    )

    monkeypatch.setattr(
        "wfm_orchestration.run_symtex_wfm_batch.load_symtex_paired_index",
        lambda _root: idx,
    )
    monkeypatch.setattr("wfm_orchestration.run_symtex_wfm_batch.load_dotenv_for_e2e", lambda: None)
    monkeypatch.setattr(
        "wfm_orchestration.run_symtex_wfm_batch.create_e2e_context",
        lambda mock_resolve=True: SimpleNamespace(
            client=None,
            model="m",
            temperature=0.0,
            max_output_tokens=8192,
            thinking_level=None,
            registry_session=None,
            llm_complete=lambda s, u: "{}",
        ),
    )

    bundle = HandoffBundle(
        schema_version="registry_persistence_v1",
        bundle_id="symtex_batch_mock_1",
        user_original_input="u",
        lines=[
            HandoffLine(line_index=1, statement_nl="x", agent3_verdict="PASS"),
        ],
    )
    snap = DevSessionSnapshot(bundle=bundle, notes="wfm_handoff_only")

    calls: list[str] = []

    def fake_runner(**kwargs):
        calls.append(kwargs["example_id"])
        return snap

    rc = run_symtex_batch(
        repo_root=tmp_path,
        limit=2,
        state_dir=tmp_path,
        rng=random.Random(42),
        skip_registry=True,
        auto_artifacts=False,
        dry_run=False,
        run_wfm=fake_runner,
    )
    assert rc == 0
    assert len(calls) == 2
    assert idx[0].manifest_example_id not in calls
    assert all("ASPBench" in c for c in calls)

    keys_after = load_completed_keys(cpath)
    assert symtex_example_key(idx[0]) in keys_after
    assert len(keys_after) == 3
