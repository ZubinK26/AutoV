from __future__ import annotations

from pivot_pipeline.ir import load_rules_and_compile, sanitize_rules_jsonable


def test_sanitize_strips_description_and_nested_junk() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "LOGICAL_IMPLICATION",
            "description": "NL echo — invalid on this model",
            "applies_to": "GLOBAL",
            "trigger_condition": {
                "kind": "atom",
                "variable": "a",
                "operator": "EQ",
                "value": True,
                "extra_atom": 1,
            },
            "required_condition": {
                "kind": "atom",
                "variable": "b",
                "operator": "EQ",
                "value": False,
            },
        }
    ]
    meta = load_rules_and_compile("p", rules)
    assert len(meta.rules) == 1
    r0 = meta.rules[0]
    assert r0.template_class == "LOGICAL_IMPLICATION"
    assert getattr(r0, "trigger_condition", None) is not None


def test_sanitize_rules_jsonable_returns_only_schema_keys() -> None:
    raw = [
        {
            "rule_id": "R1",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "x",
            "relational_operator": "LTE",
            "constant_value": 1,
            "yields": "SATISFIED",
            "notes": "drop me",
        }
    ]
    clean = sanitize_rules_jsonable(raw)
    assert "notes" not in clean[0]
    assert set(clean[0].keys()) <= {
        "rule_id",
        "template_class",
        "applies_to",
        "overrides",
        "variable",
        "relational_operator",
        "constant_value",
        "yields",
    }


def test_sanitize_default_yields_when_null_or_missing() -> None:
    for payload in (
        {
            "rule_id": "R1",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "x",
            "relational_operator": "LTE",
            "constant_value": 1,
            "yields": None,
        },
        {
            "rule_id": "R1",
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "x",
            "relational_operator": "LTE",
            "constant_value": 1,
        },
    ):
        meta = load_rules_and_compile("p", [payload])
        r0 = meta.rules[0]
        assert r0.template_class == "CONSTANT_RELATIONAL"
        assert str(r0.yields) == "SATISFIED"
