from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pivot_pipeline.assessment_linearize import (
    build_assessment_linearized,
    build_and_write_assessment_artifacts,
    rules_contain_vnext,
)
from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.ir_vnext import validate_vnext_rule_dict
from pivot_pipeline.vnext_lowering import lower_sum_threshold

FIX = Path(__file__).resolve().parent / "fixtures"


def test_assessment_linearize_k_of_n() -> None:
    body = json.loads((FIX / "vnext_k_of_n_rules.json").read_text(encoding="utf-8"))
    text = build_assessment_linearized(body["rules"])
    assert "K_OF_N at_least k=" in text
    assert "clause 1:" in text
    assert "no result_variable" in text
    assert "OR(" not in text
    assert text.strip().startswith("LINEARIZED MODEL")


def test_assessment_linearize_k_of_n_result_variable() -> None:
    body = json.loads((FIX / "vnext_k_of_n_rules.json").read_text(encoding="utf-8"))
    rules = copy.deepcopy(body["rules"])
    rules[0]["result_variable"] = "meets_competency"
    text = build_assessment_linearized(rules)
    assert "assigns result → meets_competency" in text
    assert "enforcement: via compile lowering" in text


def test_assessment_linearize_sum_threshold_multi_term() -> None:
    rule = {
        "rule_id": "R008",
        "template_class": "SUM_THRESHOLD",
        "terms": [
            {"coeff": 2, "variable": "units"},
            {"coeff": 3, "variable": "hours"},
            {"coeff": 1, "variable": "fee"},
        ],
        "relational_operator": "LTE",
        "limit": 100,
    }
    from pivot_pipeline.ir_vnext import SumThreshold

    text = build_assessment_linearized([rule])
    assert "SUM_THRESHOLD" in text
    assert "2*units" in text or "coeff=2 variable=units" in text
    assert "__acc" not in text
    assert "term 3:" in text


def test_sum_threshold_five_terms_rejected() -> None:
    from pivot_pipeline.constants import SUM_THRESHOLD_MAX_TERMS

    with pytest.raises(ValueError, match=str(SUM_THRESHOLD_MAX_TERMS)):
        validate_vnext_rule_dict(
            {
                "rule_id": "R1",
                "template_class": "SUM_THRESHOLD",
                "terms": [{"coeff": 1, "variable": f"v{i}"} for i in range(5)],
                "relational_operator": "LTE",
                "limit": 10,
            }
        )


def test_lower_sum_threshold_three_terms_emits_accumulator() -> None:
    from pivot_pipeline.ir_vnext import SumThreshold

    m = SumThreshold.model_validate(
        {
            "rule_id": "R008",
            "template_class": "SUM_THRESHOLD",
            "terms": [
                {"coeff": 2, "variable": "units"},
                {"coeff": 1, "variable": "hours"},
                {"coeff": 1, "variable": "fee"},
            ],
            "relational_operator": "LTE",
            "limit": 100,
        }
    )
    out = lower_sum_threshold(m)
    assert len(out) >= 4
    assert any(r["rule_id"] == "R008" for r in out)
    assert any("__acc" in r["rule_id"] for r in out)


def test_load_compile_z3_smoke_sum_threshold_3term() -> None:
    body = json.loads(
        (FIX / "vnext_sum_threshold_3term_rules.json").read_text(encoding="utf-8")
    )
    stats: dict = {}
    meta = load_rules_and_compile(body["policy_id"], body["rules"], lowering_stats=stats)
    assert stats.get("by_template", {}).get("SUM_THRESHOLD") == 1
    from pivot_pipeline.z3_compile import run_z3_check

    assert run_z3_check(meta)["status"] == "sat"


def test_build_and_write_assessment_artifacts(tmp_path: Path) -> None:
    body = json.loads((FIX / "vnext_k_of_n_rules.json").read_text(encoding="utf-8"))
    summary: dict = {}
    build_and_write_assessment_artifacts(
        work_dir=tmp_path, rules=body["rules"], summary=summary
    )
    assert (tmp_path / "linearized_model_for_assessment.txt").is_file()
    assert (tmp_path / "linearized_model_for_cross_critic.txt").is_file()
    assert rules_contain_vnext(body["rules"])
    assert "expansion_assessment_digest" in summary


def test_compile_still_lowers_k_of_n() -> None:
    body = json.loads((FIX / "vnext_k_of_n_rules.json").read_text(encoding="utf-8"))
    meta = load_rules_and_compile(body["policy_id"], body["rules"])
    li = [r for r in meta.rules if r.template_class == "LOGICAL_IMPLICATION"]  # type: ignore[union-attr]
    assert len(li) >= 1
