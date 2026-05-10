from __future__ import annotations

from pivot_pipeline.registry_pass import apply_registry_to_rules, build_alias_map, collect_used_slugs


def test_build_alias_map_orders_precedence_first_wins() -> None:
    reg = {"canonical_variables": [{"id": "days_since_purchase", "aliases": ["days", "num_days"]}]}
    m = build_alias_map(reg)
    assert m.get("days") == "days_since_purchase"
    assert m.get("num_days") == "days_since_purchase"


def test_apply_registry_rewrites_condition_and_fields() -> None:
    rules = [
        {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": "R0001",
            "applies_to": "GLOBAL",
            "overrides": None,
            "variable": "days",
            "relational_operator": "LTE",
            "constant_value": 30,
            "yields": "SATISFIED",
        },
        {
            "template_class": "LOGICAL_IMPLICATION",
            "rule_id": "R0002",
            "applies_to": "GLOBAL",
            "overrides": None,
            "trigger_condition": {"kind": "atom", "variable": "num_days", "operator": "GT", "value": 0},
            "required_condition": {
                "kind": "varcmp",
                "left_variable": "days",
                "operator": "EQ",
                "right_variable": "refund_flag",
            },
        },
    ]
    alias = {"days": "days_since_purchase", "num_days": "days_since_purchase"}
    out = apply_registry_to_rules(rules, alias)
    assert out[0]["variable"] == "days_since_purchase"
    assert out[1]["trigger_condition"]["variable"] == "days_since_purchase"
    assert out[1]["required_condition"]["left_variable"] == "days_since_purchase"
    assert out[1]["required_condition"]["right_variable"] == "refund_flag"


def test_collect_used_slugs_skips_rule_id_pattern() -> None:
    rules = [
        {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": "R1",
            "variable": "x",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }
    ]
    assert collect_used_slugs(rules) == ["x"]


def test_registry_pass_monkeypatch_llm() -> None:
    from pivot_pipeline import registry_pass as rp

    rules = [
        {
            "template_class": "CONSTANT_RELATIONAL",
            "rule_id": "R0001",
            "applies_to": "GLOBAL",
            "overrides": None,
            "variable": "foo_var",
            "relational_operator": "EQ",
            "constant_value": 1,
            "yields": "SATISFIED",
        }
    ]

    def fake_llm(_prompt: str) -> str:
        return '{"canonical_variables": [{"id": "foo", "aliases": ["foo_var"]}]}'

    reg, updated = rp.run_registry_pass([(1, "if foo_var then ok")], rules, llm=fake_llm)
    assert reg["canonical_variables"]
    assert updated[0]["variable"] == "foo"
