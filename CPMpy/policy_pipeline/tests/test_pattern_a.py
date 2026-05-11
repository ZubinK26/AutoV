"""Pattern A runtime tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from cpmpy_wfm_policy.runtime.pattern_a import (
    PatternAEvaluationError,
    evaluate_boolean_expr,
    gate_scalar_rules,
)
from cpmpy_wfm_policy.runtime.decision import Decision


def _root_on_syspath():
    root = Path(__file__).resolve().parents[1]
    import sys

    p = str(root)
    if p not in sys.path:
        sys.path.insert(0, p)


def _base_state() -> dict[str, int | bool]:
    return {
        "customer_kyc_status": 0,
        "customer_vulnerable_flag": False,
        "customer_recent_goodwill_total": 0,
        "account_has_sanctions_block": False,
        "transaction_amount_pence": 5000,
        "transaction_status": 0,
        "refund_call_amount_pence": 1000,
        "refund_call_type": 0,
    }


def test_evaluate_transaction_posted():
    _root_on_syspath()
    from domains.refund_example.handwritten_rules import rule_1

    st = _base_state()
    assert evaluate_boolean_expr(rule_1, st) is True
    st2 = dict(st)
    st2["transaction_status"] = 1
    assert evaluate_boolean_expr(rule_1, st2) is False


def test_gate_all_rules_clean():
    _root_on_syspath()
    from domains.refund_example.handwritten_rules import all_rules

    ok, viol, _ms = gate_scalar_rules(all_rules(), _base_state())
    assert ok and viol == []


def test_kyc_failed_violates_rule2():
    _root_on_syspath()
    from domains.refund_example.handwritten_rules import all_rules

    st = _base_state()
    st["customer_kyc_status"] = 1
    ok, viol, _ms = gate_scalar_rules(all_rules(), st)
    assert not ok
    assert "rule_2" in viol


def test_missing_state_key():
    _root_on_syspath()
    from domains.refund_example.handwritten_rules import rule_1

    with pytest.raises(PatternAEvaluationError, match="missing"):
        evaluate_boolean_expr(rule_1, {})


def test_decision_dataclass():
    d = Decision(
        allow=True,
        violated_rules=[],
        pattern_used="A",
        explanation="ok",
        solver_time_ms=1.0,
    )
    assert d.allow
