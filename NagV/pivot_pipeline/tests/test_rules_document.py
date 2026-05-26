from __future__ import annotations

import pytest

from pivot_pipeline.constants import PIVOT_IR_EXTENSIONS_MANIFEST, POLICY_SEMANTICS_VERSION_VNEXT
from pivot_pipeline.rules_document import build_rules_document, parse_rules_document


def test_build_rules_document_adds_vnext_envelope() -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "K_OF_N",
            "k": 1,
            "clauses": [{"kind": "atom", "variable": "a", "operator": "EQ", "value": 1}],
        }
    ]
    doc = build_rules_document("p", rules)
    assert doc["policy_semantics_version"] == POLICY_SEMANTICS_VERSION_VNEXT
    assert doc["pivot_ir_extensions"] == [PIVOT_IR_EXTENSIONS_MANIFEST]


def test_parse_rejects_vnext_without_1_1() -> None:
    with pytest.raises(ValueError, match="1.1"):
        parse_rules_document(
            {
                "policy_id": "p",
                "policy_semantics_version": "1.0",
                "rules": [
                    {
                        "rule_id": "R1",
                        "template_class": "INT_RANGE",
                        "variable": "x",
                        "lo": 1,
                        "hi": 2,
                    }
                ],
            }
        )
