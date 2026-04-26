"""Tests for chunked NL → WFM → shared policy pipeline (no live Gemini in default tests)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wfm_orchestration.nl_chunk_policy_pipeline import (
    format_chunk_for_wfm,
    load_or_init_progress,
    parse_nl_rules,
    run_chunk_pipeline,
    save_progress,
    snapshot_policy,
)


def test_parse_nl_rules_skips_comments_and_blank() -> None:
    text = """
# header comment

First rule here.
Second rule.

---
Third after hr.
""".strip()
    r = parse_nl_rules(text)
    assert r == ["First rule here.", "Second rule.", "Third after hr."]


def test_progress_roundtrip_hash_mismatch(tmp_path: Path) -> None:
    nl = tmp_path / "r.md"
    nl.write_text("a\nb\n", encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    p1 = load_or_init_progress(
        work / "prog.json",
        nl_path=nl,
        nl_hash="abc",
        rules_per_chunk=10,
        work_dir=work,
        force_reset=True,
    )
    save_path = work / "prog.json"
    save_progress(save_path, p1)
    p2 = load_or_init_progress(
        save_path,
        nl_path=nl,
        nl_hash="abc",
        rules_per_chunk=10,
        work_dir=work,
        force_reset=False,
    )
    assert p2.next_rule_index == 0
    with pytest.raises(ValueError, match="content changed"):
        load_or_init_progress(
            save_path,
            nl_path=nl,
            nl_hash="different",
            rules_per_chunk=10,
            work_dir=work,
            force_reset=False,
        )


def test_format_chunk_for_wfm() -> None:
    s = format_chunk_for_wfm(["a", "b"], start_index=10, file_label="x.md")
    assert "12. b" in s
    assert "11. a" in s


def test_snapshot_policy_copies(tmp_path: Path) -> None:
    pol = tmp_path / "p.lp"
    pol.write_text("foo.", encoding="utf-8")
    snap_dir = tmp_path / "snaps"
    out = snapshot_policy(pol, snapshot_dir=snap_dir, chunk_seq=0, bundle_id="b_test")
    assert out.is_file()
    assert "policy_after_chunk_0000_" in out.name
    assert (snap_dir / "policy_latest.lp").read_text(encoding="utf-8") == "foo."


def test_run_chunk_pipeline_dry_run(tmp_path: Path) -> None:
    nl = tmp_path / "in.md"
    nl.write_text("\n".join(f"Rule {i}." for i in range(25)), encoding="utf-8")
    work = tmp_path / "work"
    pol = work / "policy_model.lp"
    rc = run_chunk_pipeline(
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


def test_run_chunk_pipeline_full_mock_advances(
    tmp_path: Path,
) -> None:
    """WFM and ASP are mocked; handoff JSON is written as in a successful WFM run."""
    nl = tmp_path / "in.md"
    nl.write_text("\n".join(f"Rule {i}." for i in range(5)), encoding="utf-8")
    work = tmp_path / "work"
    pol = work / "policy_model.lp"
    work.mkdir(parents=True, exist_ok=True)
    pol.write_text("", encoding="utf-8")

    fixed_bid = "nlchunk_20990101_000000Z_aaaaaaaa"

    def fake_e2e(*args, **kwargs):
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
        patch("asp_pipeline.pipeline.run_asp_pipeline") as m_asp,
    ):
        m_asp.return_value = MagicMock(
            status="success",
            failure_reason=None,
            bundle_record_path=str(work / "asp" / f"{fixed_bid}.json"),
        )
        rc = run_chunk_pipeline(
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
    assert len(prog["chunk_records"]) == 1
    snaps = list((work / "policy_snapshots").glob("policy_after_chunk_*.lp"))
    assert len(snaps) == 1
    assert (work / "policy_snapshots" / "policy_latest.lp").is_file()


def test_pending_asp_asp_503_then_resume_skips_wfm(tmp_path: Path) -> None:
    """After WFM, if ASP fails, rerun retries ASP only (one WFM call total)."""
    nl = tmp_path / "in.md"
    nl.write_text("\n".join(f"Rule {i}." for i in range(5)), encoding="utf-8")
    work = tmp_path / "work"
    pol = work / "policy_model.lp"
    work.mkdir(parents=True, exist_ok=True)
    pol.write_text("", encoding="utf-8")
    fixed_bid = "nlchunk_20990101_000000Z_aaaaaaaa"

    def fake_e2e(*args, **kwargs):
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
                            "statement_nl": "x",
                            "agent3_verdict": "PASS",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return DevSessionSnapshot(notes="wfm_handoff_only", bundle=None)

    wfm = MagicMock(side_effect=fake_e2e)
    fail_asp = MagicMock(
        status="failed", failure_reason="503", bundle_record_path=None
    )
    ok_asp = MagicMock(
        status="success",
        failure_reason=None,
        bundle_record_path=str(work / "asp" / f"{fixed_bid}.json"),
    )

    with (
        patch("wfm_orchestration.run_metadata.new_bundle_id", lambda **k: fixed_bid),
        patch("wfm_orchestration.orchestrator.run_wfm_registry_e2e", wfm),
        patch("wfm_orchestration.e2e_context.create_e2e_context", lambda **k: MagicMock()),
        patch("asp_pipeline.pipeline.run_asp_pipeline") as m_asp,
    ):
        m_asp.side_effect = [fail_asp]
        rc1 = run_chunk_pipeline(
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
    pa = prog1.get("pending_asp")
    assert isinstance(pa, dict)
    assert pa["bundle_id"] == fixed_bid
    assert pa["rule_index_start"] == 0 and pa["rule_index_end"] == 5

    with (
        patch("wfm_orchestration.run_metadata.new_bundle_id", lambda **k: fixed_bid),
        patch("wfm_orchestration.orchestrator.run_wfm_registry_e2e", wfm),
        patch("wfm_orchestration.e2e_context.create_e2e_context", lambda **k: MagicMock()),
        patch("asp_pipeline.pipeline.run_asp_pipeline") as m_asp2,
    ):
        m_asp2.side_effect = [ok_asp]
        rc2 = run_chunk_pipeline(
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
    assert m_asp2.call_count == 1
    prog2 = json.loads((work / "nl_chunk_progress.json").read_text(encoding="utf-8"))
    assert prog2["next_rule_index"] == 5
    assert prog2.get("pending_asp") is None
    assert len(prog2["chunk_records"]) == 1
    assert prog2["chunk_records"][0]["bundle_id"] == fixed_bid
