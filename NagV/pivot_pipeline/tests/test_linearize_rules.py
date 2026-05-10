from __future__ import annotations

import json
from pathlib import Path

import pytest

from pivot_pipeline.linearize_rules import linearize_rules_for_cross_critic

_FIXTURE_RULES = (
    Path(__file__).resolve().parents[2] / "exports" / "pivot_runs_test_input2" / "rules_extracted.json"
)


@pytest.mark.skipif(not _FIXTURE_RULES.is_file(), reason="pivot_runs_test_input2 export not in tree")
def test_linearize_rules_contains_outcome_split_example() -> None:
    body = json.loads(_FIXTURE_RULES.read_text(encoding="utf-8"))
    rules = body["rules"]
    text = linearize_rules_for_cross_critic(rules)
    assert "R0015" in text
    assert "R0020" in text
    assert "R0020" in text
    assert "LOGICAL_IMPLICATION" in text
    assert "decision" in text or "request_is_denied" in text


def test_linearize_minimal_rule() -> None:
    rules = [
        {
            "rule_id": "R0001",
            "applies_to": "GLOBAL",
            "overrides": None,
            "template_class": "CONSTANT_RELATIONAL",
            "variable": "n",
            "relational_operator": "LTE",
            "constant_value": 3,
            "yields": "SATISFIED",
        }
    ]
    s = linearize_rules_for_cross_critic(rules)
    assert "R0001 | CONSTANT_RELATIONAL | n LTE 3 | yields SATISFIED" in s
