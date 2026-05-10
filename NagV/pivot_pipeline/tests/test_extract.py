from __future__ import annotations

import pytest

from pivot_pipeline.extract import (
    ExtractValidationError,
    extract_one_line,
    extract_one_line_with_repairs,
    is_abort_response,
    validate_preemption_cross_rule_targets,
    validate_rule_dict,
)


def test_is_abort() -> None:
    assert is_abort_response("ABORT: Ruleset exceeds decidable scope.")
    assert not is_abort_response('{"template_class": "CONSTANT_RELATIONAL"}')


def test_extract_one_line_monkeypatch() -> None:
    tmpl = "Return JSON only.\n<<<LINE>>>"

    def fake_llm(prompt: str) -> str:
        assert "hello" in prompt
        return (
            '{"template_class":"CONSTANT_RELATIONAL","variable":"x",'
            '"relational_operator":"EQ","constant_value":1,"yields":"SATISFIED"}'
        )

    r = extract_one_line(1, "hello", tmpl=tmpl, llm=fake_llm)
    assert r["rule_id"] == "R0001"
    assert r["variable"] == "x"


def test_validate_rule_dict_rejects_unknown_class() -> None:
    with pytest.raises(ExtractValidationError, match="line 3"):
        validate_rule_dict({"template_class": "UNKNOWN", "rule_id": "R1"}, line_index=3)


def test_schema_repair_second_llm_call_fixes_json(monkeypatch: pytest.MonkeyPatch) -> None:
    tmpl = "Return JSON only.\n<<<LINE>>>"
    calls: list[str] = []

    good = (
        '{"template_class":"CONSTANT_RELATIONAL","rule_id":"R0001","applies_to":"GLOBAL",'
        '"overrides":null,"variable":"x","relational_operator":"EQ",'
        '"constant_value":1,"yields":"SATISFIED"}'
    )

    def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return "```json\n{ broken"
        return good

    monkeypatch.setenv("PIVOT_EXTRACT_SCHEMA_REPAIR_MAX", "2")
    r = extract_one_line_with_repairs(
        1,
        "hello",
        tmpl=tmpl,
        llm=fake_llm,
        prior_rules=[],
        apply_cross_rule=False,
    )
    assert r["variable"] == "x"
    assert len(calls) == 2


def test_preemption_cross_rule_targets() -> None:
    prior_ok = [{"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL"}]
    prior_bad = [
        {"rule_id": "R0001", "template_class": "CONSTANT_RELATIONAL"},
        {"rule_id": "R0002", "template_class": "PREEMPTION"},
    ]
    rule = {
        "template_class": "PREEMPTION",
        "rule_id": "R0003",
        "applies_to": "GLOBAL",
        "overrides": None,
        "preempting_condition": {"kind": "atom", "variable": "x", "operator": "EQ", "value": 1},
        "action": "BYPASS_RULE",
        "target_rule_id": "R0001",
    }
    validate_preemption_cross_rule_targets(rule, line_index=3, prior_rules=prior_ok)

    with pytest.raises(ExtractValidationError, match="non-null"):
        validate_preemption_cross_rule_targets(
            {**rule, "target_rule_id": None}, line_index=3, prior_rules=prior_ok
        )

    with pytest.raises(ExtractValidationError, match="earlier"):
        validate_preemption_cross_rule_targets(
            {**rule, "target_rule_id": "R0099"}, line_index=3, prior_rules=prior_ok
        )

    with pytest.raises(ExtractValidationError, match="PREEMPTION"):
        validate_preemption_cross_rule_targets(
            {**rule, "target_rule_id": "R0002"}, line_index=3, prior_rules=prior_bad
        )


def test_sequential_extract_passes_prior_for_cross_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    from pivot_pipeline.extract import extract_rules_from_lines

    tmpl = "x\n<<<LINE>>>"
    atom = {"kind": "atom", "variable": "v", "operator": "EQ", "value": True}

    line_state = {"i": 0}

    def fake_llm(prompt: str) -> str:
        line_state["i"] += 1
        if line_state["i"] == 1:
            return (
                '{"template_class":"CONSTANT_RELATIONAL","applies_to":"GLOBAL","overrides":null,'
                '"variable":"v","relational_operator":"EQ","constant_value":true,"yields":"SATISFIED"}'
            )
        return (
            '{"template_class":"PREEMPTION","applies_to":"GLOBAL","overrides":null,'
            '"preempting_condition":'
            + __import__("json").dumps(atom)
            + ',"action":"BYPASS_RULE","target_rule_id":"R0001"}'
        )

    monkeypatch.setattr("pivot_pipeline.extract._extract_prompt_template", lambda: tmpl)
    monkeypatch.setenv("PIVOT_EXTRACT_WORKERS", "1")
    monkeypatch.setenv("PIVOT_EXTRACT_SCHEMA_REPAIR_MAX", "0")

    rules = extract_rules_from_lines(
        ["Line one.", "Preempt line."],
        llm=fake_llm,
        max_workers=1,
    )
    assert len(rules) == 2
    assert rules[0]["rule_id"] == "R0001"
    assert rules[1]["template_class"] == "PREEMPTION"
    assert rules[1]["target_rule_id"] == "R0001"
