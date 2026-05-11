"""Manifest routing + combined A/B gate_tool."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from cpmpy_wfm_policy.pipeline.ast_validator import load_signature_namespace
from cpmpy_wfm_policy.runtime.router import (
    RouterError,
    assert_manifest_routing_consistent,
    gate_tool,
    partition_rules_by_manifest,
)


def _root():
    r = Path(__file__).resolve().parents[1]
    if str(r) not in sys.path:
        sys.path.insert(0, str(r))
    return r


def _slots_sig_path() -> Path:
    return _root() / "domains" / "slots_alldiff" / "signature.py"


def test_manifest_misroute_raises():
    bad = {
        "rules": [
            {
                "id": "rule_1",
                "uses_global_constraints": True,
                "uses_vector_variables": False,
                "pattern": "A",
            }
        ]
    }
    with pytest.raises(RouterError, match="misroute"):
        assert_manifest_routing_consistent(bad)


def test_partition_slots_all_b():
    _root()
    from domains.slots_alldiff import handwritten_rules as hr

    manifest = {
        "rules": [
            {
                "id": "rule_1",
                "uses_global_constraints": True,
                "uses_vector_variables": False,
                "pattern": "B",
            }
        ]
    }
    a, b = partition_rules_by_manifest(hr.all_rules(), manifest)
    assert a == {} and set(b) == {"rule_1"}


def test_gate_tool_slots_allow_and_block():
    _root()
    from domains.slots_alldiff import handwritten_rules as hr
    from domains.slots_alldiff.fixtures.per_rule import base_state

    sig = load_signature_namespace(str(_slots_sig_path()))
    manifest = {
        "rules": [
            {
                "id": "rule_1",
                "uses_global_constraints": True,
                "uses_vector_variables": False,
                "pattern": "B",
            }
        ]
    }
    d_ok = gate_tool(
        all_rules=hr.all_rules(),
        manifest=manifest,
        state=base_state(),
        signature_namespace=sig,
    )
    assert d_ok.allow
    d_bad = gate_tool(
        all_rules=hr.all_rules(),
        manifest=manifest,
        state={"slot_a": 0, "slot_b": 0, "slot_c": 1},
        signature_namespace=sig,
    )
    assert not d_bad.allow
    assert "rule_1" in d_bad.violated_rules


def test_gate_tool_refund_all_a():
    _root()
    from domains.refund_example import handwritten_rules as hr

    sig_path = _root() / "domains" / "refund_example" / "signature.py"
    sig = load_signature_namespace(str(sig_path))
    rules = hr.all_rules()
    manifest = {
        "rules": [
            {
                "id": rid,
                "uses_global_constraints": False,
                "uses_vector_variables": False,
                "pattern": "A",
            }
            for rid in sorted(rules.keys())
        ]
    }
    from domains.refund_example.fixtures.per_rule import base_state

    st = base_state()
    d = gate_tool(
        all_rules=rules,
        manifest=manifest,
        state=st,
        signature_namespace=sig,
    )
    assert d.allow
    assert d.pattern_used == "A"
