from __future__ import annotations

import pytest

pytest.importorskip("z3")

from agentsim_simplified.entities import ToolCall
from agentsim_simplified.policy_source import default_refined_policy_path
from agentsim_simplified.runner import run_scenario
from agentsim_simplified.seed_data import load_db
from agentsim_simplified.simpl_checker import SimplPolicyChecker, SimplVerdict
from agentsim_simplified.simpl_scenario import RefundCallScenario
from agentsim_simplified.tools import lookup_bundle
from agentsim_simplified.validator import validate_apply_refund


@pytest.fixture(scope="module")
def checker() -> SimplPolicyChecker:
    p = default_refined_policy_path()
    if not p.is_file():
        pytest.skip(f"missing refined policy: {p}")
    return SimplPolicyChecker(policy_path=p)


def test_policy_file_exists_and_sat(checker: SimplPolicyChecker) -> None:
    assert checker.policy_path.is_file()


def test_scenario_demo_allow_and_blocks(checker: SimplPolicyChecker) -> None:
    trace = run_scenario(checker=checker)
    gated = [e for e in trace if e.tool_name == "apply_refund"]
    assert len(gated) == 5
    assert gated[0].decision == "ALLOW"
    assert all(e.decision == "BLOCK" for e in gated[1:])


@pytest.mark.parametrize(
    "txid,amount,rtype,expect_permit",
    [
        ("T-001", 3000, "MERCHANT_REFUND", True),
        ("T-004", 2000, "MERCHANT_REFUND", False),
        ("T-005", 3000, "MERCHANT_REFUND", False),
        ("T-003", 1000, "GOODWILL_CREDIT", False),
        ("T-006", 10000, "MERCHANT_REFUND", False),
        ("T-007", 100, "MERCHANT_REFUND", False),
    ],
)
def test_grounded_states(
    checker: SimplPolicyChecker, txid: str, amount: int, rtype: str, expect_permit: bool
) -> None:
    db = load_db()
    b = lookup_bundle(db, txid)
    call = ToolCall(
        "apply_refund",
        {"transaction_id": txid, "amount_pence": amount, "refund_type": rtype, "reason": "test"},
    )
    d = validate_apply_refund(b, call, checker=checker)
    assert d.allow is expect_permit


def test_missing_entity_blocks(checker: SimplPolicyChecker) -> None:
    call = ToolCall(
        "apply_refund",
        {
            "transaction_id": "T-NONE",
            "amount_pence": 100,
            "refund_type": "MERCHANT_REFUND",
            "reason": "x",
        },
    )
    scen = RefundCallScenario.from_bundle(None, refund_type="MERCHANT_REFUND", refund_amount_pence=100)
    assert checker.decide(scen).verdict != SimplVerdict.PERMITTED
