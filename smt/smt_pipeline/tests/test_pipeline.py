import json
from pathlib import Path

import pytest

from smt_pipeline.config import SmtPipelineConfig
from smt_pipeline.models import CriticContext, FormalizerContext
from smt_pipeline.pipeline import run_smt_pipeline


def _handoff(
    path: Path,
    *,
    bundle_id: str = "b_testbundle0000001",
    lines: list[dict] | None = None,
) -> None:
    if lines is None:
        lines = [
            {"line_index": 0, "statement_nl": "All cats are pets.", "agent3_verdict": "PASS"},
        ]
    payload = {
        "schema_version": "registry_persistence_v1",
        "bundle_id": bundle_id,
        "user_original_input": "test",
        "lines": lines,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_block_for_rule(rid: str, line_idx: int, *, include_set_logic: bool = True) -> str:
    lines = [
        f"; Rule: {rid}  |  Line: {line_idx}",
        r'; NL: "test"',
    ]
    if include_set_logic:
        lines.append("(set-logic ALL)")
    lines.append("(assert true)")
    return "\n".join(lines)


def test_first_commit_empty_policy(tmp_path):
    handoff = tmp_path / "h.json"
    policy = tmp_path / "policy_model.smt2"
    bundles = tmp_path / "bundles"
    _handoff(handoff)

    rule_ids_seen: list[str] = []

    def formalizer(ctx: FormalizerContext) -> str:
        rid = ctx.in_scope_lines[0].split()[0].split("=")[1]
        rule_ids_seen.append(rid)
        return _valid_block_for_rule(rid, 0)

    def critic(ctx: CriticContext) -> dict:
        return {"approved": True, "objections": []}

    cfg = SmtPipelineConfig(parse_timeout_sec=30.0)
    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=cfg,
        formalizer_fn=formalizer,
        critic_fn=critic,
    )
    assert res.status == "success"
    assert policy.is_file()
    text = policy.read_text(encoding="utf-8")
    assert "assert true" in text.lower() or "assert true" in text
    rec = json.loads((bundles / f"{res.bundle_id}.json").read_text(encoding="utf-8"))
    assert rec["pipeline_status"] == "committed"
    assert rec["failure_reason"] is None


def test_second_bundle_appends(tmp_path):
    handoff1 = tmp_path / "h1.json"
    handoff2 = tmp_path / "h2.json"
    policy = tmp_path / "policy_model.smt2"
    bundles = tmp_path / "bundles"
    _handoff(handoff1, bundle_id="b_bundle_one0000001")
    _handoff(
        handoff2,
        bundle_id="b_bundle_two0000002",
        lines=[{"line_index": 0, "statement_nl": "Second rule.", "agent3_verdict": "PASS"}],
    )

    def formalizer(ctx: FormalizerContext) -> str:
        rid = ctx.in_scope_lines[0].split()[0].split("=")[1]
        # Avoid duplicate (set-logic ...) when appending — Z3 rejects multiple set-logic.
        inc = not ctx.policy_text.strip()
        return _valid_block_for_rule(rid, 0, include_set_logic=inc)

    def critic(ctx: CriticContext) -> dict:
        return {"approved": True, "objections": []}

    cfg = SmtPipelineConfig(parse_timeout_sec=30.0)
    r1 = run_smt_pipeline(
        handoff_path=handoff1,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=cfg,
        formalizer_fn=formalizer,
        critic_fn=critic,
    )
    assert r1.status == "success"
    r2 = run_smt_pipeline(
        handoff_path=handoff2,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=cfg,
        formalizer_fn=formalizer,
        critic_fn=critic,
    )
    assert r2.status == "success"
    full = policy.read_text(encoding="utf-8")
    assert "b_bundle_one0000001" in full
    assert "b_bundle_two0000002" in full


def test_out_of_scope_no_rule_ids(tmp_path):
    handoff = tmp_path / "h.json"
    policy = tmp_path / "policy_model.smt2"
    bundles = tmp_path / "bundles"
    _handoff(
        handoff,
        lines=[
            {"line_index": 0, "statement_nl": "skip me", "agent3_verdict": "OUT_OF_SCOPE"},
        ],
    )
    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(),
        formalizer_fn=lambda ctx: "",
        critic_fn=lambda ctx: {"approved": True, "objections": []},
    )
    assert res.status == "success"
    assert not policy.is_file()
    rec = json.loads((bundles / f"{res.bundle_id}.json").read_text(encoding="utf-8"))
    assert rec["out_of_scope_line_indices"] == [0]
    assert rec["rule_ids"] == []


def test_syntax_fail_after_retries(tmp_path):
    handoff = tmp_path / "h.json"
    policy = tmp_path / "policy_model.smt2"
    bundles = tmp_path / "bundles"
    _handoff(handoff)

    n = {"c": 0}

    def formalizer(ctx: FormalizerContext) -> str:
        n["c"] += 1
        return "((( not smt2"

    def critic(ctx: CriticContext) -> dict:
        pytest.fail("critic should not run")

    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(syntax_repair_cap=3),
        formalizer_fn=formalizer,
        critic_fn=critic,
    )
    assert res.status == "failed"
    assert res.failure_reason == "SYNTAX_FAIL"
    assert n["c"] == 3


def test_semantic_fail(tmp_path):
    handoff = tmp_path / "h.json"
    policy = tmp_path / "policy_model.smt2"
    bundles = tmp_path / "bundles"
    _handoff(handoff)

    def formalizer(ctx: FormalizerContext) -> str:
        rid = ctx.in_scope_lines[0].split()[0].split("=")[1]
        return _valid_block_for_rule(rid, 0)

    n = {"c": 0}

    def critic(ctx: CriticContext) -> dict:
        n["c"] += 1
        return {"approved": False, "objections": [{"rule_id": "x", "line_index": 0, "issue_type": "other", "description": "no"}]}

    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(semantic_repair_cap=3),
        formalizer_fn=formalizer,
        critic_fn=critic,
    )
    assert res.status == "failed"
    assert res.failure_reason == "SEMANTIC_FAIL"
    assert n["c"] == 4


def test_size_cap(tmp_path):
    policy = tmp_path / "policy_model.smt2"
    lines = []
    for i in range(49):
        lines.append(f"; Rule: r_{i:04d}ruleid  |  Line: 0")
        lines.append("(assert true)")
    policy.write_text("\n".join(lines), encoding="utf-8")

    handoff = tmp_path / "h.json"
    bundles = tmp_path / "bundles"
    _handoff(
        handoff,
        lines=[
            {"line_index": 0, "statement_nl": "a", "agent3_verdict": "PASS"},
            {"line_index": 1, "statement_nl": "b", "agent3_verdict": "PASS"},
        ],
    )

    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(rule_cap=50),
        formalizer_fn=lambda ctx: pytest.fail("no formalizer"),
        critic_fn=lambda ctx: pytest.fail("no critic"),
    )
    assert res.status == "failed"
    assert res.failure_reason == "SIZE_CAP_REACHED"


def test_policy_corrupt(tmp_path):
    policy = tmp_path / "policy_model.smt2"
    policy.write_text("(( invalid", encoding="utf-8")
    handoff = tmp_path / "h.json"
    bundles = tmp_path / "bundles"
    _handoff(handoff)
    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(),
        formalizer_fn=lambda ctx: pytest.fail("no formalizer"),
        critic_fn=lambda ctx: pytest.fail("no critic"),
    )
    assert res.status == "failed"
    assert res.failure_reason == "POLICY_MODEL_CORRUPT"


def test_context_limit(tmp_path):
    policy = tmp_path / "policy_model.smt2"
    handoff = tmp_path / "h.json"
    bundles = tmp_path / "bundles"
    _handoff(handoff)
    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(context_char_limit=10),
        formalizer_fn=lambda ctx: pytest.fail("no formalizer"),
        critic_fn=lambda ctx: pytest.fail("no critic"),
    )
    assert res.status == "failed"
    assert res.failure_reason == "CONTEXT_LIMIT_EXCEEDED"


def test_bundle_id_generated_when_missing(tmp_path):
    handoff = tmp_path / "h.json"
    policy = tmp_path / "policy_model.smt2"
    bundles = tmp_path / "bundles"
    payload = {
        "schema_version": "registry_persistence_v1",
        "user_original_input": "x",
        "lines": [{"line_index": 0, "statement_nl": "x", "agent3_verdict": "OUT_OF_SCOPE"}],
    }
    handoff.write_text(json.dumps(payload), encoding="utf-8")
    res = run_smt_pipeline(
        handoff_path=handoff,
        policy_model_path=policy,
        bundle_out_dir=bundles,
        cfg=SmtPipelineConfig(),
        formalizer_fn=lambda ctx: "",
        critic_fn=lambda ctx: {"approved": True, "objections": []},
    )
    assert res.bundle_id.startswith("b_")
    assert len(res.bundle_id) == 2 + 16
