from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.ir import (
    ConstantRelational,
    LogicalImplication,
    load_rules_and_compile,
)
from pivot_pipeline.ir_vnext import KOfN, validate_vnext_rule_dict
from pivot_pipeline.vnext_lowering import (
    LoweringStats,
    expand_rules_to_core,
    lower_int_range,
    lower_k_of_n,
)

FIX = Path(__file__).resolve().parent / "fixtures"


def test_int_range_lowers_to_gte_lte_pair() -> None:
    rule = {
        "rule_id": "R1",
        "template_class": "INT_RANGE",
        "variable": "n",
        "lo": 2,
        "hi": 5,
        "yields": "SATISFIED",
    }
    from pivot_pipeline.ir_vnext import IntRange

    m = validate_vnext_rule_dict(rule)
    assert isinstance(m, IntRange)
    out = lower_int_range(m)
    assert len(out) == 2
    assert out[0]["template_class"] == "CONSTANT_RELATIONAL"
    assert out[0]["relational_operator"] == "GTE"
    assert out[1]["relational_operator"] == "LTE"


def test_int_range_equal_bounds_single_eq() -> None:
    from pivot_pipeline.ir_vnext import IntRange

    m = IntRange.model_validate(
        {
            "rule_id": "R1",
            "template_class": "INT_RANGE",
            "variable": "n",
            "lo": 7,
            "hi": 7,
        }
    )
    out = lower_int_range(m)
    assert len(out) == 1
    assert out[0]["relational_operator"] == "EQ"
    assert out[0]["constant_value"] == 7


def test_k_of_n_handoff_filter_count() -> None:
    from pivot_pipeline.ir_vnext import IntRange

    m = KOfN.model_validate(
        {
            "rule_id": "R1",
            "template_class": "K_OF_N",
            "k": 2,
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": 1},
                {"kind": "atom", "variable": "b", "operator": "EQ", "value": 1},
                {"kind": "atom", "variable": "c", "operator": "EQ", "value": 1},
            ],
        }
    )
    out = lower_k_of_n(m)
    assert len(out) == 1
    assert out[0]["template_class"] == "LOGICAL_IMPLICATION"


def test_k_of_n_lowering_result_variable_binds_aggregate() -> None:
    m = KOfN.model_validate(
        {
            "rule_id": "R1",
            "template_class": "K_OF_N",
            "k": 2,
            "result_variable": "meets_competency",
            "clauses": [
                {"kind": "atom", "variable": "a", "operator": "EQ", "value": True},
                {"kind": "atom", "variable": "b", "operator": "EQ", "value": True},
            ],
        }
    )
    out = lower_k_of_n(m)
    assert len(out) == 1
    req = out[0]["required_condition"]
    assert req["kind"] == "atom"
    assert req["variable"] == "meets_competency"
    assert req["operator"] == "EQ"
    assert req["value"] is True


def test_expand_rules_to_core_preserves_core_templates() -> None:
    core = [
        {
            "rule_id": "R1",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "x",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }
    ]
    out = expand_rules_to_core(core)
    assert out == core


def test_load_compile_z3_smoke_k_of_n() -> None:
    body = json.loads((FIX / "vnext_k_of_n_rules.json").read_text(encoding="utf-8"))
    stats: dict = {}
    meta = load_rules_and_compile(body["policy_id"], body["rules"], lowering_stats=stats)
    assert stats.get("by_template", {}).get("K_OF_N") == 1
    assert all(
        r.template_class in ("LOGICAL_IMPLICATION",)  # type: ignore[union-attr]
        for r in meta.rules
    )
    from pivot_pipeline.z3_compile import run_z3_check

    assert run_z3_check(meta)["status"] == "sat"


def test_load_compile_z3_smoke_all_templates() -> None:
    body = json.loads((FIX / "vnext_all_templates_rules.json").read_text(encoding="utf-8"))
    stats: dict = {}
    meta = load_rules_and_compile(body["policy_id"], body["rules"], lowering_stats=stats)
    assert len(stats.get("by_template", {})) == 8
    core_classes = {r.template_class for r in meta.rules}  # type: ignore[union-attr]
    assert "INT_RANGE" not in core_classes
    assert "K_OF_N" not in core_classes
    assert "CONSTANT_RELATIONAL" in core_classes or "LOGICAL_IMPLICATION" in core_classes
    from pivot_pipeline.z3_compile import run_z3_check

    z3 = run_z3_check(meta)
    assert z3["status"] == "sat"


def test_k_of_n_rejects_k_out_of_range() -> None:
    with pytest.raises(ValueError, match="1 <= k <= n"):
        validate_vnext_rule_dict(
            {
                "rule_id": "R1",
                "template_class": "K_OF_N",
                "k": 5,
                "clauses": [
                    {"kind": "atom", "variable": "a", "operator": "EQ", "value": 1},
                ],
            }
        )


def test_lowering_stats_dataclass() -> None:
    st = LoweringStats()
    rules = json.loads((FIX / "vnext_int_range_rules.json").read_text(encoding="utf-8"))["rules"]
    expand_rules_to_core(rules, stats=st)
    assert st.by_template.get("INT_RANGE") == 1
    assert st.core_rules_emitted >= 2
