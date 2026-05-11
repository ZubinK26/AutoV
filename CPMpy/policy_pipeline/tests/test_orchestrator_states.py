"""Orchestrator state machine + emit artifacts (mocked LLMs)."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

from cpmpy_wfm_policy.pipeline.orchestrator import (
    OrchestratorConfig,
    OrchestratorState,
    run_orchestrator,
)


def _refund_domain() -> Path:
    return Path(__file__).resolve().parents[1] / "domains" / "refund_example"


def _seed_mini_domain(tmp: Path, *, lines: list[str], copy_fixtures: bool = True) -> Path:
    d = tmp / "bundle"
    d.mkdir()
    src = _refund_domain()
    shutil.copy2(src / "signature.py", d / "signature.py")
    shutil.copy2(src / "glossary.md", d / "glossary.md")
    if copy_fixtures:
        (d / "fixtures").mkdir()
        shutil.copy2(src / "fixtures" / "per_rule.py", d / "fixtures" / "per_rule.py")
    shutil.copy2(src / "tools.json", d / "tools.json")
    (d / "rules.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def test_orchestrator_happy_path_one_rule(tmp_path: Path):
    dom = _seed_mini_domain(tmp_path, lines=["Transaction must be POSTED."])
    out = tmp_path / "out"
    payload = {
        "rule_module": "import cpmpy as cp\nrule_1 = transaction_is_posted\n",
        "used_symbols": ["transaction_is_posted"],
        "uses_global_constraints": False,
        "uses_vector_variables": False,
    }

    def formalizer(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(payload)

    res = run_orchestrator(
        domain_dir=dom,
        out_dir=out,
        formalizer_llm=formalizer,
        cfg=OrchestratorConfig(
            max_repairs_per_rule=0,
            medium_hypothesis_examples=5,
            enable_roundtrip=False,
        ),
    )
    assert res.success
    assert OrchestratorState.LOAD_INPUTS.value in res.states
    assert OrchestratorState.BATCH_VERIFY.value in res.states
    assert OrchestratorState.CONSISTENCY_CHECK.value in res.states
    assert OrchestratorState.EMIT_POLICY.value in res.states
    assert OrchestratorState.RUNTIME_READY.value in res.states
    assert (out / "policy.py").is_file()
    assert (out / "manifest.json").is_file()
    assert (out / "consistency_report.json").is_file()
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["schema_version"] == "cpmpy_policy_manifest_v1"
    assert len(man["rules"]) == 1
    assert man["rules"][0]["pattern"] == "A"
    assert man["rules"][0]["nl_source"] == "Transaction must be POSTED."

    spec = importlib.util.spec_from_file_location("orch_policy_test", out / "policy.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.rule_1 is not None
    assert "rule_1" in mod.all_rules()
    log = (out / "verification_log.jsonl").read_text(encoding="utf-8")
    assert "cheap_check_ok" in log
    assert "medium_cumulative_sat_ok" in log
    assert "medium_hypothesis_smoke_ok" in log
    assert "roundtrip" in log
    cr = json.loads((out / "consistency_report.json").read_text(encoding="utf-8"))
    assert cr["schema_version"] == "cpmpy_consistency_report_v1"
    assert cr["joint_sat"] is True


def test_orchestrator_repair_then_ok(tmp_path: Path):
    dom = _seed_mini_domain(tmp_path, lines=["KYC must pass."], copy_fixtures=False)
    out = tmp_path / "out2"
    good = {
        "rule_module": "import cpmpy as cp\nrule_1 = ~customer_kyc_failed\n",
        "used_symbols": ["customer_kyc_failed"],
        "uses_global_constraints": False,
        "uses_vector_variables": False,
    }
    n = 0

    def formalizer(*, system_instruction: str, user_text: str) -> str:
        nonlocal n
        n += 1
        if n == 1:
            return "not-json"
        return json.dumps(good)

    def diagnoser(*, system_instruction: str, user_text: str) -> str:
        return json.dumps(
            {
                "failure_class": "formalizer_json",
                "formalizer_hint": "Output one JSON object only.",
            }
        )

    res = run_orchestrator(
        domain_dir=dom,
        out_dir=out,
        formalizer_llm=formalizer,
        diagnoser_llm=diagnoser,
        cfg=OrchestratorConfig(
            max_repairs_per_rule=2,
            enable_roundtrip=False,
            max_llm_json_retries=1,
        ),
    )
    assert res.success
    assert n == 2
    assert OrchestratorState.REPAIR.value in res.states
    log_lines = (out / "verification_log.jsonl").read_text(encoding="utf-8").strip().splitlines()
    events = [json.loads(ln)["event"] for ln in log_lines]
    assert "diagnosis" in events


def test_manifest_pattern_b_from_flags(tmp_path: Path):
    from cpmpy_wfm_policy.pipeline.formalizer import FormalizerOutput
    from cpmpy_wfm_policy.pipeline.orchestrator import emit_manifest

    outs = [
        FormalizerOutput(
            rule_index=1,
            rule_name="rule_1",
            rule_module="import cpmpy as cp\nrule_1 = transaction_is_posted\n",
            used_symbols=frozenset({"transaction_is_posted"}),
            uses_global_constraints=True,
            uses_vector_variables=False,
            raw_response="",
        )
    ]
    emit_manifest(
        outputs=outs,
        nl_lines=["placeholder"],
        dest=tmp_path / "manifest.json",
        policy_version="testver",
    )
    man = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert man["rules"][0]["pattern"] == "B"
