from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.template_generator_agent import run_template_generator, run_template_generator_pipeline
from pivot_pipeline.template_generator_context import build_template_generator_context

FIX = Path(__file__).resolve().parent / "fixtures"
TOY_RULES = FIX / "template_suite_toy_rules.json"
TOY_SUITE = FIX / "template_suite_toy_suite.json"


def _seed_workdir(tmp: Path) -> None:
    data = json.loads(TOY_RULES.read_text(encoding="utf-8"))
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "rules_extracted.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    meta = load_rules_and_compile(data["policy_id"], data["rules"])
    (tmp / "meta_scheme.json").write_text(meta.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (tmp / "synthetic_en.md").write_text("# synthetic stub\n", encoding="utf-8")


def test_build_template_generator_context(tmp_path: Path) -> None:
    _seed_workdir(tmp_path)
    ctx = build_template_generator_context(tmp_path)
    assert "R1" in ctx
    assert "template_toy" in ctx


def test_run_template_generator_mock_llm(tmp_path: Path) -> None:
    _seed_workdir(tmp_path)
    suite_json = TOY_SUITE.read_text(encoding="utf-8")

    def fake_llm(_prompt: str) -> str:
        return suite_json

    suite, raw = run_template_generator(work_dir=tmp_path, llm_complete=fake_llm, max_rounds=1)
    assert len(suite.instances) >= 1
    assert "schema_version" in raw or len(raw) > 0


def test_run_template_generator_retry_then_ok(tmp_path: Path) -> None:
    _seed_workdir(tmp_path)
    ok = TOY_SUITE.read_text(encoding="utf-8")
    n = {"calls": 0}

    def flaky(_p: str) -> str:
        n["calls"] += 1
        if n["calls"] == 1:
            return "not json"
        return ok

    suite, _ = run_template_generator(work_dir=tmp_path, llm_complete=flaky, max_rounds=3)
    assert suite.suite_id == "toy_all_kinds"


def test_run_template_generator_pipeline_writes_file(tmp_path: Path) -> None:
    _seed_workdir(tmp_path)
    ok = TOY_SUITE.read_text(encoding="utf-8")

    path = run_template_generator_pipeline(
        work_dir=tmp_path,
        llm_complete=lambda _p: ok,
        max_rounds=1,
    )
    assert path.name == "template_suite_generated.json"
    assert path.is_file()
    assert (tmp_path / "template_generator_raw.txt").is_file()


def test_run_template_generator_validation_failure_exhausts(tmp_path: Path) -> None:
    _seed_workdir(tmp_path)

    def bad(_p: str) -> str:
        return json.dumps({"schema_version": "2", "suite_id": "x", "instances": []})

    with pytest.raises(Exception):
        run_template_generator(work_dir=tmp_path, llm_complete=bad, max_rounds=2)
