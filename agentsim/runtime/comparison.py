from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from agentsim.runtime.models import ToolCall
from agentsim.runtime.scenario_runner import run_write_steps
from agentsim.runtime.snapshot import full_snapshot_builder, policy_v0_text
from agentsim.runtime.z3_legality import Z3LegalityChecker

WRITE_TOOL_NAMES = frozenset(
    {
        "initiate_dispute",
        "cancel_dispute",
        "apply_refund",
        "apply_goodwill_credit",
        "apply_fee_reversal",
        "freeze_card",
        "unfreeze_card",
        "apply_account_restriction",
        "lift_account_restriction",
        "report_fraud",
        "escalate_to_human",
        "request_documentation",
        "send_customer_message",
        "log_consumer_duty_assessment",
    },
)


class ScenarioContextProto(Protocol):
    conn: sqlite3.Connection
    interaction_id: str
    write_tools: Any


@dataclass
class VanillaGatedMetrics:
    scenario_id: str
    write_steps: int
    vanilla_would_block_posthoc: int
    gated_live_blocks: int
    gated_writes_allowed: int
    gated_force_escalation_events: int


def _audit_write_stats(
    conn: sqlite3.Connection,
    interaction_id: str,
) -> tuple[int, int, int]:
    cur = conn.execute(
        """
        SELECT tool_name, decision FROM audit_log
        WHERE interaction_id = ?
        ORDER BY id ASC
        """,
        (interaction_id,),
    )
    blocks = allows = 0
    for row in cur.fetchall():
        tn, dec = row["tool_name"], row["decision"]
        if tn not in WRITE_TOOL_NAMES:
            continue
        if dec == "BLOCK":
            blocks += 1
        elif dec == "ALLOW":
            allows += 1
    row_fe = conn.execute(
        """
        SELECT COUNT(*) AS c FROM audit_log
        WHERE interaction_id = ? AND tool_name = 'force_escalation_guard'
        """,
        (interaction_id,),
    ).fetchone()
    fe = int(row_fe["c"]) if row_fe else 0
    return blocks, allows, fe


def compare_vanilla_vs_gated(
    make_context_vanilla: Any,
    make_context_gated: Any,
    scenario: dict[str, Any],
    *,
    checker: Z3LegalityChecker | None = None,
) -> VanillaGatedMetrics:
    """Vanilla = always-allow then post-hoc Z3; gated = live enforcement (expected Z3 executor)."""

    steps = scenario.get("steps", [])
    sid = str(scenario.get("id", "unknown"))
    write_steps = sum(1 for s in steps if s.get("op") == "write")

    chk = checker or Z3LegalityChecker(policy_v0_text())

    vctx = make_context_vanilla()
    bldr = full_snapshot_builder(vctx.conn, interaction_id=vctx.interaction_id)
    fixed_ts = datetime.now(timezone.utc)
    trail: list[tuple[ToolCall, dict[str, Any]]] = []

    for s in steps:
        if s.get("op") != "write":
            continue
        tool = s["tool"]
        args = dict(s.get("args", {}))
        call = ToolCall(
            tool_name=tool,
            parameters=args,
            proposed_at=fixed_ts,
            interaction_id=vctx.interaction_id,
        )
        trail.append((call, bldr(call)))
        getattr(vctx.write_tools, tool)(**args)

    posthoc_blocks = sum(1 for call, snap in trail if not chk.validate_call(call, snap).allow)

    gctx = make_context_gated()
    run_write_steps(gctx, steps)
    gb, ga, fe = _audit_write_stats(gctx.conn, gctx.interaction_id)

    return VanillaGatedMetrics(
        scenario_id=sid,
        write_steps=write_steps,
        vanilla_would_block_posthoc=posthoc_blocks,
        gated_live_blocks=gb,
        gated_writes_allowed=ga,
        gated_force_escalation_events=fe,
    )
