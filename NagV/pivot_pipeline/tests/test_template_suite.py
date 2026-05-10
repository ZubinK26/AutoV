from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.template_suite.diff import diff_instance
from pivot_pipeline.template_suite.schemas import parse_instance_dict
from pivot_pipeline.template_suite.run import run_template_suite
from pivot_pipeline.template_suite.validate import validate_instance
from pivot_pipeline.ir import load_rules_and_compile


FIX_DIR = Path(__file__).resolve().parent / "fixtures"
RULES = FIX_DIR / "template_suite_toy_rules.json"
SUITE = FIX_DIR / "template_suite_toy_suite.json"


def _meta():
    data = json.loads(RULES.read_text(encoding="utf-8"))
    return load_rules_and_compile(data["policy_id"], data["rules"])


def test_toy_suite_all_pass() -> None:
    report = run_template_suite(
        suite_path=SUITE,
        rules_extracted_path=RULES,
        write_report=False,
    )
    assert report["summary"]["failed"] == 0
    assert report["summary"]["errors"] == 0
    assert report["summary"]["inconclusive"] == 0
    assert report["summary"]["passed"] == len(report["results"])


def test_validate_rejects_bad_decision_golden() -> None:
    raw = {
        "template_kind": "decision_query",
        "instance_id": "x",
        "world": {},
        "query": {"decision_metric": "rule", "rule_id": "R1"},
        "golden": {"decision": "ALLOW"},
    }
    inst = parse_instance_dict(raw)
    with pytest.raises(ValueError, match="satisfied"):
        validate_instance(_meta(), inst)


def test_diff_pairwise_expect_equal_false_fails() -> None:
    from pivot_pipeline.template_suite.schemas import PairwiseInstance

    inst = PairwiseInstance(
        instance_id="p",
        world={},
        query_a={"amount": 50},
        query_b={"amount": 60},
        query={"decision_metric": "rule", "rule_id": "R1"},
        golden={"expect_equal": False},
    )
    actual = {"z3_status_a": "sat", "z3_status_b": "sat", "decision_a": "satisfied", "decision_b": "satisfied"}
    v, d = diff_instance(inst, actual)
    assert v == "fail"
    assert d["match"] is False


def test_run_writes_report(tmp_path: Path) -> None:
    out = tmp_path / "template_run_report.json"
    run_template_suite(suite_path=SUITE, rules_extracted_path=RULES, out_report_path=out, write_report=True)
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "results" in data


def test_run_py_template_phase_after_final_critic_block() -> None:
    """Regression: executable template suite runs after pivot + cross + final semantic critic paths."""
    run_py = Path(__file__).resolve().parents[1] / "run.py"
    src = run_py.read_text(encoding="utf-8")
    i_final_varprod = src.find("varprod trigger IR check failed after final semantic")
    i_template = src.find("if with_template_generator or template_suite_path is not None:")
    i_warnings = src.find("warnings: list[str] = []")
    assert i_final_varprod != -1 and i_template != -1 and i_warnings != -1
    assert i_final_varprod < i_template < i_warnings
