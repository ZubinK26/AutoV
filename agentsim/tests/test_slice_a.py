import pytest

from agentsim.runtime.harness import ScenarioHarness
from agentsim.runtime.models import AuditDecision


@pytest.fixture
def harness():
    return ScenarioHarness(policy_version="test-policy")


def test_slice_a_read_only_scenario_audits_na(harness: ScenarioHarness):
    ctx = harness.begin_scenario(customer_id="C-001")
    rt = ctx.read_tools

    assert rt.lookup_customer("C-001") is not None
    assert rt.lookup_customer("missing") is None

    acc = rt.lookup_account("A-001")
    assert acc is not None
    assert acc.customer_id == "C-001"

    txs = rt.list_recent_transactions("A-001", 10)
    assert len(txs) >= 2
    assert rt.lookup_transaction("T-001") is not None

    assert rt.lookup_dispute("D-001") is not None
    assert len(rt.list_customer_disputes("C-001", 5)) >= 1

    assert len(rt.check_account_restrictions("A-001")) == 1

    assert rt.lookup_fraud_report("F-001") is not None
    assert rt.check_section_75_eligibility("T-001") is True
    assert rt.check_section_75_eligibility("T-002") is False

    cur = ctx.conn.execute(
        "SELECT decision, COUNT(*) FROM audit_log GROUP BY decision"
    )
    rows = {r[0]: r[1] for r in cur.fetchall()}
    assert rows.get(AuditDecision.NA.value) == 11
    assert AuditDecision.ALLOW.value not in rows and AuditDecision.BLOCK.value not in rows

    cur2 = ctx.conn.execute(
        "SELECT COUNT(*) FROM audit_log WHERE interaction_id = ?",
        (ctx.interaction_id,),
    )
    assert cur2.fetchone()[0] == 11


def test_harness_creates_fresh_interaction(harness: ScenarioHarness):
    ctx = harness.begin_scenario(customer_id="C-001")
    cur = ctx.conn.execute(
        "SELECT customer_id FROM interaction WHERE interaction_id = ?",
        (ctx.interaction_id,),
    )
    assert cur.fetchone()[0] == "C-001"
