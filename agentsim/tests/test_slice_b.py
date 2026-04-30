import pytest

from agentsim.runtime.harness import ScenarioHarness
from agentsim.runtime.models import AuditDecision, Decision, ToolBlockedResult, ToolCall
from agentsim.runtime.validator_stub import always_allow_validate, never_allow_validate


@pytest.fixture
def harness():
    return ScenarioHarness(policy_version="test-policy")


def test_write_tools_stub_allow_and_audit(harness: ScenarioHarness):
    ctx = harness.begin_scenario(customer_id="C-001")
    wt = ctx.write_tools
    cur0 = ctx.conn.execute(
        "SELECT balance_pence FROM account WHERE account_id = ?",
        ("A-001",),
    )
    bal_before = cur0.fetchone()[0]

    d2 = wt.initiate_dispute(
        "T-002",
        "GOODS_NOT_RECEIVED",
        "Parcel never arrived",
    )
    assert not isinstance(d2, ToolBlockedResult)
    assert d2.transaction_id == "T-002"

    wt.cancel_dispute(d2.dispute_id, "customer withdrew")

    rf = wt.apply_refund(
        "T-002",
        500,
        "MERCHANT_REFUND",
        "merchant agreed",
    )
    assert not isinstance(rf, ToolBlockedResult)

    gw = wt.apply_goodwill_credit("C-001", 100, "gesture")
    assert not isinstance(gw, ToolBlockedResult)

    frv = wt.apply_fee_reversal("T-002", "incorrect fee")
    assert not isinstance(frv, ToolBlockedResult)

    wt.freeze_card("K-001", "customer request sim")
    wt.unfreeze_card("K-001", "resolved")

    wt.lift_account_restriction("R-001", "review complete")
    wt.apply_account_restriction("A-001", "AML_REVIEW", "triggered in test")

    fr = wt.report_fraud("C-001", ["T-002"], "APP_FRAUD")
    assert not isinstance(fr, ToolBlockedResult)

    inter = wt.escalate_to_human("complex case", "HIGH")
    assert not isinstance(inter, ToolBlockedResult)
    assert inter.escalated_to_human is True

    doc = wt.request_documentation("C-001", "PROOF_OF_ADDRESS", "2026-05-01")
    assert doc is None

    msg = wt.send_customer_message("C-001", "Hello", "SERVICE")
    assert msg is None

    cda = wt.log_consumer_duty_assessment(
        "C-001",
        ["stress"],
        {
            "fair_value_check_passed": True,
            "clear_communication_check_passed": True,
        },
    )
    assert not isinstance(cda, ToolBlockedResult)

    cur = ctx.conn.execute("SELECT decision, COUNT(*) FROM audit_log GROUP BY decision")
    counts = {r[0]: r[1] for r in cur.fetchall()}
    assert counts.get(AuditDecision.ALLOW.value) == 14
    assert counts.get(AuditDecision.BLOCK.value) is None
    curb = ctx.conn.execute(
        "SELECT balance_pence FROM account WHERE account_id = ?",
        ("A-001",),
    )
    bal_after = curb.fetchone()[0]
    assert bal_after > bal_before


def test_write_blocked_records_block_audit(harness: ScenarioHarness):
    def block_messages(call: ToolCall, _state: dict) -> Decision:
        if call.tool_name == "send_customer_message":
            return Decision(allow=False, unsat_core=["R-X"], explanation="no outbound in test")
        return always_allow_validate(call, _state)

    ctx = harness.begin_scenario(customer_id="C-001", validate_call=block_messages)
    r = ctx.write_tools.send_customer_message("C-001", "x", "PROMOTIONAL")
    assert isinstance(r, ToolBlockedResult)
    row = ctx.conn.execute(
        "SELECT decision, explanation FROM audit_log ORDER BY id DESC LIMIT 1",
    ).fetchone()
    assert row[0] == AuditDecision.BLOCK.value
    assert "no outbound" in (row[1] or "")


def test_never_allow_validator(harness: ScenarioHarness):
    ctx = harness.begin_scenario(customer_id="C-001", validate_call=never_allow_validate)
    out = ctx.write_tools.freeze_card("K-001", "nope")
    assert isinstance(out, ToolBlockedResult)
