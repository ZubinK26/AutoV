from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.varprod_trigger_validate import (
    linearize_varprod_rules_excerpt,
    validate_varprod_triggers,
    varprod_skip_rule_ids_from_env,
)


def _good_r3() -> dict:
    return {
        "rule_id": "R0003",
        "template_class": "LOGICAL_IMPLICATION",
        "trigger_condition": {
            "kind": "and",
            "children": [
                {"kind": "atom", "variable": "a", "operator": "GTE", "value": 0},
                {"kind": "atom", "variable": "b", "operator": "GTE", "value": 0},
            ],
        },
        "required_condition": {
            "kind": "varprod_cmp",
            "left_variable": "a",
            "right_variable": "b",
            "operator": "LTE",
            "rhs": {"kind": "const", "value": 120},
        },
    }


def _bad_r3_missing_b_in_trigger() -> dict:
    return {
        "rule_id": "R0003",
        "template_class": "LOGICAL_IMPLICATION",
        "trigger_condition": {"kind": "atom", "variable": "a", "operator": "GTE", "value": 0},
        "required_condition": {
            "kind": "varprod_cmp",
            "left_variable": "a",
            "right_variable": "b",
            "operator": "LTE",
            "rhs": {"kind": "const", "value": 120},
        },
    }


def test_varprod_trigger_ok_when_both_factors_in_trigger() -> None:
    rules = [_good_r3()]
    assert validate_varprod_triggers(rules) == []


def test_varprod_trigger_fails_when_factor_missing_from_trigger() -> None:
    rules = [_bad_r3_missing_b_in_trigger()]
    issues = validate_varprod_triggers(rules)
    assert len(issues) == 1
    assert "R0003" in issues[0]
    assert "b" in issues[0]


def test_varprod_skip_rule_ids_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PIVOT_VARPROD_TRIGGER_SKIP_RULE_IDS", "R0003, R0009")
    assert varprod_skip_rule_ids_from_env() == {"R0003", "R0009"}
    assert validate_varprod_triggers([_bad_r3_missing_b_in_trigger()], skip_rule_ids={"R0003"}) == []


def test_linearize_varprod_excerpt_filters() -> None:
    rules = [
        _good_r3(),
        {
            "rule_id": "Rx",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "x",
            "relational_operator": "LTE",
            "constant_value": 1,
            "yields": "SATISFIED",
        },
    ]
    ex = linearize_varprod_rules_excerpt(rules)
    assert "R0003" in ex
    assert "Rx" not in ex


_FIXTURE = (
    Path(__file__).resolve().parents[2] / "exports" / "pivot_runs_test_input2" / "rules_extracted.json"
)


@pytest.mark.skipif(not _FIXTURE.is_file(), reason="export fixture not present")
def test_test_input2_export_current_state_varprod_trigger() -> None:
    """Regression: weak R0003 trigger (only one factor in trigger) must fail the check."""
    body = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    issues = validate_varprod_triggers(body["rules"])
    if issues:
        assert any("R0003" in s for s in issues)
    else:
        r3 = next(r for r in body["rules"] if r.get("rule_id") == "R0003")
        from pivot_pipeline.varprod_trigger_validate import (
            collect_variables_in_condition,
            iter_varprod_factor_pairs,
        )

        tvars = collect_variables_in_condition(r3["trigger_condition"])
        req = r3["required_condition"]
        for left, right in iter_varprod_factor_pairs(req):
            assert left in tvars and right in tvars
