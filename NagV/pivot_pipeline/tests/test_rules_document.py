from __future__ import annotations

import json

import pytest

from pivot_pipeline.constants import PIVOT_IR_EXTENSIONS_MANIFEST, POLICY_SEMANTICS_VERSION_VNEXT
from pivot_pipeline.rules_document import (
    build_rules_document,
    parse_rules_document,
    write_rules_document_file,
)


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


def test_parse_normalizes_stripped_vnext_envelope() -> None:
    _pid, _rules, meta = parse_rules_document(
        {
            "policy_id": "p",
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
    assert meta["policy_semantics_version"] == POLICY_SEMANTICS_VERSION_VNEXT
    assert meta["pivot_ir_extensions"] == [PIVOT_IR_EXTENSIONS_MANIFEST]


def test_write_rules_document_file_preserves_vnext(tmp_path) -> None:
    rules = [
        {
            "rule_id": "R1",
            "template_class": "K_OF_N",
            "k": 1,
            "clauses": [{"kind": "atom", "variable": "a", "operator": "EQ", "value": 1}],
        }
    ]
    path = tmp_path / "rules_extracted.json"
    write_rules_document_file(path, "p", rules)
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["policy_semantics_version"] == POLICY_SEMANTICS_VERSION_VNEXT
    assert body["pivot_ir_extensions"] == [PIVOT_IR_EXTENSIONS_MANIFEST]
