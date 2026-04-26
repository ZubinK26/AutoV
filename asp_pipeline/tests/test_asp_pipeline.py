import json
from pathlib import Path

import pytest

from asp_pipeline.config import AspPipelineConfig
from asp_pipeline.models import AspCriticContext, AspFormalizerContext
from asp_pipeline.pipeline import run_asp_pipeline


def _handoff(
    path: Path,
    *,
    bundle_id: str = "b_test_asp_0001",
) -> None:
    payload = {
        "schema_version": "registry_persistence_v1",
        "bundle_id": bundle_id,
        "user_original_input": "test",
        "lines": [
            {"line_index": 0, "statement_nl": "Every cat is a pet.", "agent3_verdict": "PASS"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _lp_minimal(rule_id: str) -> str:
    return f"""% Bundle: t
% Rule: {rule_id}  |  line_index: 0  |  NL: "x"
#const n = 0.
all_ok.
"""


def test_asp_first_commit_patched_clingo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = tmp_path / "h.json"
    pol = tmp_path / "p.lp"
    out = tmp_path / "b"
    _handoff(h, bundle_id="b_asp1")

    def fake_pg(*_a, **_k):
        return (True, "", "")

    def fake_po(*_a, **_k):
        return (True, "")

    def fake_g(*_a, **_k):
        return (True, "")

    monkeypatch.setattr("asp_pipeline.pipeline.check_parse_and_ground", fake_pg)
    monkeypatch.setattr("asp_pipeline.pipeline.check_parse_only", fake_po)
    monkeypatch.setattr("asp_pipeline.pipeline.check_ground", fake_g)

    def f(ctx: AspFormalizerContext) -> str:
        rid = ctx.in_scope_lines[0].split()[0].split("=")[1]
        return _lp_minimal(rid)

    def c(_ctx: AspCriticContext) -> dict:
        return {
            "approved": True,
            "verdicts": [{"line_index": 0, "approved": True, "issue": ""}],
        }

    r = run_asp_pipeline(
        handoff_path=h,
        policy_model_path=pol,
        bundle_out_dir=out,
        cfg=AspPipelineConfig(
            clingo_parse_timeout_sec=1.0,
            clingo_ground_timeout_sec=1.0,
        ),
        formalizer_fn=f,
        critic_fn=c,
    )
    assert r.status == "success"
    assert pol.is_file()
    assert "% Bundle" in pol.read_text(encoding="utf-8")
    rec = json.loads((out / f"{r.bundle_id}.json").read_text(encoding="utf-8"))
    assert rec["pipeline_status"] == "committed"
    assert rec.get("pipeline_kind") == "asp_clincon"
    assert rec.get("formalizer_prompt") == "formalizer_new.md"
    assert rec.get("formalizer_prompt_sha256")


def test_asp_critic_repair_then_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    h = tmp_path / "h.json"
    pol = tmp_path / "p.lp"
    out = tmp_path / "b"
    _handoff(h, bundle_id="b_asp2")

    monkeypatch.setattr(
        "asp_pipeline.pipeline.check_parse_and_ground",
        lambda *a, **k: (True, "", ""),
    )
    monkeypatch.setattr("asp_pipeline.pipeline.check_parse_only", lambda *a, **k: (True, ""))
    monkeypatch.setattr("asp_pipeline.pipeline.check_ground", lambda *a, **k: (True, ""))

    n_form: list[int] = [0]

    def f(_ctx: AspFormalizerContext) -> str:
        n_form[0] += 1
        return _lp_minimal("r_fix")

    def c(_ctx: AspCriticContext) -> dict:
        if n_form[0] < 2:
            return {"approved": False, "verdicts": [], "overall_issue": "improve it"}
        return {
            "approved": True,
            "verdicts": [{"line_index": 0, "approved": True, "issue": ""}],
        }

    r = run_asp_pipeline(
        handoff_path=h,
        policy_model_path=pol,
        bundle_out_dir=out,
        cfg=AspPipelineConfig(semantic_repair_cap=2),
        formalizer_fn=f,
        critic_fn=c,
    )
    assert r.status == "success"
    assert n_form[0] == 2
