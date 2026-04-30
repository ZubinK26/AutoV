import pytest

pytest.importorskip("z3")

from agentsim.runtime.comparison import compare_vanilla_vs_gated
from agentsim.runtime.fabrication import fabrication_check_stub
from agentsim.runtime.harness import ScenarioHarness
from agentsim.runtime.models import ToolBlockedResult


def test_compare_vanilla_vs_gated_goodwill_blocked():
    scenario = {
        "id": "unit_blocked",
        "customer_id": "C-002",
        "steps": [
            {
                "op": "write",
                "tool": "apply_goodwill_credit",
                "args": {"customer_id": "C-002", "amount_pence": 60000, "reason": "x"},
            },
        ],
    }

    def mv():
        return ScenarioHarness(policy_version="u-v").begin_scenario_always_allow_full_snapshots(
            customer_id="C-002",
        )

    def mg():
        return ScenarioHarness(policy_version="u-g").begin_scenario(
            customer_id="C-002",
            use_builtin_z3_policy=True,
        )

    m = compare_vanilla_vs_gated(mv, mg, scenario)
    assert m.write_steps == 1
    assert m.vanilla_would_block_posthoc == 1
    assert m.gated_live_blocks == 1
    assert m.gated_writes_allowed == 0


def test_force_escalation_after_repeated_blocks():
    ctx = ScenarioHarness(policy_version="fe").begin_scenario(
        customer_id="C-002",
        use_builtin_z3_policy=True,
        repeated_block_limit=3,
    )
    for _ in range(3):
        r = ctx.write_tools.apply_goodwill_credit("C-002", 60000, "retry")
        assert isinstance(r, ToolBlockedResult)

    row = ctx.conn.execute(
        "SELECT escalated_to_human FROM interaction WHERE interaction_id = ?",
        (ctx.interaction_id,),
    ).fetchone()
    assert row is not None and row["escalated_to_human"] == 1
    nfe = ctx.conn.execute(
        "SELECT COUNT(*) AS c FROM audit_log WHERE tool_name = 'force_escalation_guard'",
    ).fetchone()
    assert int(nfe["c"]) == 1


def test_fabrication_stub_always_ok():
    r = fabrication_check_stub("I refunded you GBP 500", _interaction_id="I-x")
    assert r.ok and r.issues == []
