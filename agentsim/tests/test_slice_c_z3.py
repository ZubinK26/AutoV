import pytest

pytest.importorskip("z3")

from agentsim.runtime.harness import ScenarioHarness
from agentsim.runtime.models import AuditDecision, ToolBlockedResult


@pytest.fixture
def harness_z3():
    return ScenarioHarness(policy_version="policy-v0")


def test_z3_blocks_goodwill_over_cap_for_vulnerable(harness_z3: ScenarioHarness):
    # C-002 is vulnerable in seed_minimal.json
    ctx = harness_z3.begin_scenario(
        customer_id="C-002",
        use_builtin_z3_policy=True,
    )
    out = ctx.write_tools.apply_goodwill_credit("C-002", 60_000, "too much")
    assert isinstance(out, ToolBlockedResult)
    assert "R-VULN-GOODWILL-CAP" in (out.unsat_core or [])
    row = ctx.conn.execute(
        "SELECT COUNT(*) FROM refund WHERE customer_id = ?",
        ("C-002",),
    ).fetchone()
    assert row[0] == 0
    aud = ctx.conn.execute(
        "SELECT decision FROM audit_log WHERE tool_name = ? ORDER BY id DESC LIMIT 1",
        ("apply_goodwill_credit",),
    ).fetchone()
    assert aud[0] == AuditDecision.BLOCK.value


def test_z3_allows_goodwill_under_cap_for_vulnerable(harness_z3: ScenarioHarness):
    ctx = harness_z3.begin_scenario(
        customer_id="C-002",
        use_builtin_z3_policy=True,
    )
    out = ctx.write_tools.apply_goodwill_credit("C-002", 40_000, "ok")
    assert not isinstance(out, ToolBlockedResult)
    assert out.amount_pence == 40_000
    aud = ctx.conn.execute(
        "SELECT decision FROM audit_log WHERE tool_name = ?",
        ("apply_goodwill_credit",),
    ).fetchone()
    assert aud[0] == AuditDecision.ALLOW.value


def test_z3_allows_high_goodwill_for_non_vulnerable(harness_z3: ScenarioHarness):
    ctx = harness_z3.begin_scenario(
        customer_id="C-001",
        use_builtin_z3_policy=True,
    )
    out = ctx.write_tools.apply_goodwill_credit("C-001", 80_000, "premium gesture")
    assert not isinstance(out, ToolBlockedResult)
    assert out.amount_pence == 80_000


def test_z3_other_writes_still_allowed(harness_z3: ScenarioHarness):
    ctx = harness_z3.begin_scenario(
        customer_id="C-001",
        use_builtin_z3_policy=True,
    )
    c = ctx.write_tools.freeze_card("K-001", "test")
    assert not isinstance(c, ToolBlockedResult)
