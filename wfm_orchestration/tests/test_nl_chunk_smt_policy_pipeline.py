"""Tests for chunked NL → WFM (smt) → shared policy_model.smt2 (no live Gemini by default)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wfm_orchestration.nl_chunk_smt_policy_pipeline import (
    NlChunkSmtProgress,
    _heal_stale_pending_smt,
    _is_smt_committed,
    load_or_init_progress,
    run_chunk_smt_pipeline,
    save_progress,
    snapshot_policy_smt,
)


def test_smt_committed(tmp_path: Path) -> None:
    bid = "x"
    assert not _is_smt_committed(tmp_path, bid)
    (tmp_path / f"{bid}.json").write_text(
        json.dumps({"bundle_id": bid, "pipeline_status": "failed"}), encoding="utf-8"
    )
    assert not _is_smt_committed(tmp_path, bid)
    (tmp_path / f"{bid}.json").write_text(
        json.dumps({"bundle_id": bid, "pipeline_status": "committed"}), encoding="utf-8"
    )
    assert _is_smt_committed(tmp_path, bid)


def test_snapshot_policy_smt(tmp_path: Path) -> None:
    pol = tmp_path / "p.smt2"
    pol.write_text("(set-logic ALL)", encoding="utf-8")
    snap_dir = tmp_path / "snaps"
    out = snapshot_policy_smt(pol, snapshot_dir=snap_dir, chunk_seq=1, bundle_id="b1")
    assert out.suffix == ".smt2"
    assert (snap_dir / "policy_latest.smt2").read_text(encoding="utf-8") == "(set-logic ALL)"


def test_run_chunk_smt_dry_run(tmp_path: Path) -> None:
    nl = tmp_path / "in.md"
    nl.write_text("\n".join(f"Rule {i}." for i in range(25)), encoding="utf-8")
    work = tmp_path / "work"
    pol = work / "policy_model.smt2"
    rc = run_chunk_smt_pipeline(
        repo_root=tmp_path,
        nl_file=nl,
        work_dir=work,
        policy_model=pol,
        rules_per_chunk=10,
        dry_run=True,
        force_reset=True,
        print_fn=lambda *a, **k: None,
    )
    assert rc == 0


def test_heal_stale_pending_smt(tmp_path: Path) -> None:
    prog = NlChunkSmtProgress(
        pending_smt={
            "bundle_id": "bid1",
            "rule_index_start": 0,
            "rule_index_end": 3,
            "chunk_seq": 0,
        },
        next_rule_index=0,
    )
    bundles = tmp_path / "smt"
    bundles.mkdir()
    (bundles / "bid1.json").write_text(
        json.dumps({"pipeline_status": "committed", "bundle_id": "bid1"}), encoding="utf-8"
    )
    pp = tmp_path / "nl_chunk_progress.json"
    save_progress(pp, prog)
    ok = _heal_stale_pending_smt(prog, smt_bundles=bundles, progress_path=pp, print_fn=lambda *a: None)
    assert ok
    assert prog.next_rule_index == 3
    assert prog.pending_smt is None


def test_full_mock_advances(tmp_path: Path) -> None:
    nl = tmp_path / "in.md"
    nl.write_text("\n".join(f"Rule {i}." for i in range(5)), encoding="utf-8")
    work = tmp_path / "work"
    pol = work / "policy_model.smt2"
    work.mkdir(parents=True, exist_ok=True)
    pol.write_text("", encoding="utf-8")
    fixed_bid = "nlchunksmt_20990101_000000Z_bbbbbbbb"

    def fake_e2e(*args, **kwargs):
        assert kwargs.get("wfm_profile") == "smt"
        from registry_stage.models import DevSessionSnapshot

        hp = kwargs.get("handoff_json")
        assert hp is not None
        Path(hp).parent.mkdir(parents=True, exist_ok=True)
        Path(hp).write_text(
            json.dumps(
                {
                    "schema_version": "registry_persistence_v1",
                    "bundle_id": fixed_bid,
                    "user_original_input": "u",
                    "lines": [
                        {
                            "line_index": 0,
                            "statement_nl": "Every cat is a pet.",
                            "agent3_verdict": "PASS",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return DevSessionSnapshot(notes="wfm_handoff_only", bundle=None)

    with (
        patch("wfm_orchestration.run_metadata.new_bundle_id", lambda **k: fixed_bid),
        patch("wfm_orchestration.orchestrator.run_wfm_registry_e2e", side_effect=fake_e2e),
        patch("wfm_orchestration.e2e_context.create_e2e_context", lambda **k: MagicMock()),
        patch("smt_pipeline.pipeline.run_smt_pipeline") as m_smt,
    ):
        m_smt.return_value = MagicMock(
            status="success",
            failure_reason=None,
            bundle_record_path=str(work / "smt_bundles" / f"{fixed_bid}.json"),
        )
        rc = run_chunk_smt_pipeline(
            repo_root=tmp_path,
            nl_file=nl,
            work_dir=work,
            policy_model=pol,
            rules_per_chunk=10,
            dry_run=False,
            force_reset=True,
            print_fn=lambda *a, **k: None,
        )
    assert rc == 0
    prog = json.loads((work / "nl_chunk_progress.json").read_text(encoding="utf-8"))
    assert prog["next_rule_index"] == 5
    assert prog.get("pending_smt") is None
    snaps = list((work / "policy_snapshots").glob("policy_after_chunk_*.smt2"))
    assert len(snaps) == 1


def test_pending_smt_503_resume_skips_wfm(tmp_path: Path) -> None:
    nl = tmp_path / "in.md"
    nl.write_text("\n".join(f"Rule {i}." for i in range(5)), encoding="utf-8")
    work = tmp_path / "work"
    pol = work / "policy_model.smt2"
    work.mkdir(parents=True, exist_ok=True)
    pol.write_text("", encoding="utf-8")
    fixed_bid = "nlchunksmt_20990101_000000Z_cccccccc"

    def fake_e2e(*args, **kwargs):
        from registry_stage.models import DevSessionSnapshot

        hp = kwargs.get("handoff_json")
        Path(hp).parent.mkdir(parents=True, exist_ok=True)
        Path(hp).write_text(
            json.dumps(
                {
                    "schema_version": "registry_persistence_v1",
                    "bundle_id": fixed_bid,
                    "user_original_input": "u",
                    "lines": [
                        {"line_index": 0, "statement_nl": "x", "agent3_verdict": "PASS"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        return DevSessionSnapshot(notes="wfm_handoff_only", bundle=None)

    wfm = MagicMock(side_effect=fake_e2e)
    fail_smt = MagicMock(status="failed", failure_reason="503", bundle_record_path=None)
    ok_smt = MagicMock(
        status="success",
        failure_reason=None,
        bundle_record_path=str(work / "smt" / f"{fixed_bid}.json"),
    )

    with (
        patch("wfm_orchestration.run_metadata.new_bundle_id", lambda **k: fixed_bid),
        patch("wfm_orchestration.orchestrator.run_wfm_registry_e2e", wfm),
        patch("wfm_orchestration.e2e_context.create_e2e_context", lambda **k: MagicMock()),
        patch("smt_pipeline.pipeline.run_smt_pipeline") as m_smt,
    ):
        m_smt.side_effect = [fail_smt]
        rc1 = run_chunk_smt_pipeline(
            repo_root=tmp_path,
            nl_file=nl,
            work_dir=work,
            policy_model=pol,
            rules_per_chunk=10,
            dry_run=False,
            force_reset=True,
            print_fn=lambda *a, **k: None,
        )
    assert rc1 == 1
    assert wfm.call_count == 1
    prog1 = json.loads((work / "nl_chunk_progress.json").read_text(encoding="utf-8"))
    assert prog1["next_rule_index"] == 0
    ps = prog1.get("pending_smt")
    assert isinstance(ps, dict)
    assert ps["bundle_id"] == fixed_bid

    with (
        patch("wfm_orchestration.run_metadata.new_bundle_id", lambda **k: fixed_bid),
        patch("wfm_orchestration.orchestrator.run_wfm_registry_e2e", wfm),
        patch("wfm_orchestration.e2e_context.create_e2e_context", lambda **k: MagicMock()),
        patch("smt_pipeline.pipeline.run_smt_pipeline") as m_smt2,
    ):
        m_smt2.side_effect = [ok_smt]
        rc2 = run_chunk_smt_pipeline(
            repo_root=tmp_path,
            nl_file=nl,
            work_dir=work,
            policy_model=pol,
            rules_per_chunk=10,
            dry_run=False,
            force_reset=False,
            print_fn=lambda *a, **k: None,
        )
    assert rc2 == 0
    assert wfm.call_count == 1
    assert m_smt2.call_count == 1
    prog2 = json.loads((work / "nl_chunk_progress.json").read_text(encoding="utf-8"))
    assert prog2["next_rule_index"] == 5
    assert prog2.get("pending_smt") is None


def test_hash_mismatch_raises(tmp_path: Path) -> None:
    nl = tmp_path / "r.md"
    nl.write_text("a\n", encoding="utf-8")
    work = tmp_path / "work"
    p = work / "p.json"
    save_progress(
        p,
        load_or_init_progress(
            p, nl_path=nl, nl_hash="abc", rules_per_chunk=10, work_dir=work, force_reset=True
        ),
    )
    with pytest.raises(ValueError, match="content changed"):
        load_or_init_progress(
            p,
            nl_path=nl,
            nl_hash="wrong",
            rules_per_chunk=10,
            work_dir=work,
            force_reset=False,
        )
