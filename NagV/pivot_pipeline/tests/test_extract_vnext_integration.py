from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.constants import SUM_THRESHOLD_MAX_TERMS
from pivot_pipeline.extract import ExtractValidationError, validate_rule_dict
from pivot_pipeline.ir import load_rules_and_compile, sanitize_rules_jsonable
from pivot_pipeline.ir_vnext import VNEXT_TEMPLATE_CLASSES

FIX = Path(__file__).resolve().parent / "fixtures"


def test_extract_model_map_accepts_all_vnext_templates() -> None:
    body = json.loads((FIX / "extract_vnext_golden_rules.json").read_text(encoding="utf-8"))
    for i, rule in enumerate(body["rules"], start=1):
        out = validate_rule_dict(rule, line_index=i)
        assert out["template_class"] in VNEXT_TEMPLATE_CLASSES


def test_golden_vnext_rules_compile_after_lowering() -> None:
    from pivot_pipeline.rules_document import parse_rules_document

    body = json.loads((FIX / "extract_vnext_golden_rules.json").read_text(encoding="utf-8"))
    policy_id, rules, envelope = parse_rules_document(body)
    stats: dict = {}
    meta = load_rules_and_compile(
        policy_id,
        rules,
        lowering_stats=stats,
        policy_semantics_version=envelope.get("policy_semantics_version"),
    )
    assert len(stats.get("by_template", {})) == 8
    assert "K_OF_N" not in {r.template_class for r in meta.rules}  # type: ignore[union-attr]


def test_sum_threshold_five_terms_rejected_at_validate() -> None:
    with pytest.raises(ExtractValidationError, match=str(SUM_THRESHOLD_MAX_TERMS)):
        validate_rule_dict(
            {
                "rule_id": "R1",
                "template_class": "SUM_THRESHOLD",
                "terms": [{"coeff": 1, "variable": f"v{i}"} for i in range(5)],
                "relational_operator": "LTE",
                "limit": 1,
            },
            line_index=1,
        )


def test_sanitize_vnext_strips_extra_keys() -> None:
    rule = {
        "rule_id": "R1",
        "template_class": "K_OF_N",
        "k": 1,
        "clauses": [{"kind": "atom", "variable": "a", "operator": "EQ", "value": 1}],
        "description": "remove me",
    }
    clean = sanitize_rules_jsonable([rule])[0]
    assert "description" not in clean
    assert clean["template_class"] == "K_OF_N"


def test_repairer_mock_k_of_n_compiles() -> None:
    rule = {
        "rule_id": "R0001",
        "template_class": "K_OF_N",
        "k": 1,
        "clauses": [
            {"kind": "atom", "variable": "a", "operator": "EQ", "value": 1},
            {"kind": "atom", "variable": "b", "operator": "EQ", "value": 1},
        ],
    }
    meta = load_rules_and_compile("t", [rule])
    assert any(r.template_class == "LOGICAL_IMPLICATION" for r in meta.rules)  # type: ignore[union-attr]
