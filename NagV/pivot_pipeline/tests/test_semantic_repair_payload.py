from pivot_pipeline.test_repair_rules_payload import (
    build_rules_payload_stubs,
    focus_rule_ids_from_handoff,
    merge_repairer_output,
    payload_rules_json_size,
)


def test_focus_from_critic_handoff() -> None:
    handoff = {
        "findings": [
            {
                "id": "C001",
                "rule_ids": ["R0036", "R0037"],
                "explanation": "wire R0034",
            }
        ]
    }
    ids = focus_rule_ids_from_handoff(handoff)
    assert ids == ["R0034", "R0036", "R0037"]


def test_stub_payload_smaller_than_full() -> None:
    full = [
        {
            "rule_id": f"R{i:04d}",
            "template_class": "LOGICAL_IMPLICATION",
            "trigger_condition": {"kind": "atom", "variable": f"v{i}", "operator": "EQ", "value": True},
            "required_condition": {"kind": "atom", "variable": f"out{i}", "operator": "EQ", "value": True},
            "applies_to": "GLOBAL",
        }
        for i in range(30)
    ]
    focus = ["R0001", "R0005"]
    stubbed = build_rules_payload_stubs(full, focus)
    full_b, stub_b = payload_rules_json_size(full, stubbed)
    assert stub_b < full_b
    merged = merge_repairer_output(full_rules=full, repairer_rules=stubbed, focus_rule_ids=focus)
    assert len(merged) == 30
