"""
Run the full write-tool matrix: fresh DB per tool, snapshot + validator, audit trail.

Designed so a WFM → SMT policy file can replace the bundled policy without
changing this orchestration.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from agentsim.runtime.harness import ScenarioHarness, ValidateFn
from agentsim.runtime.models import Channel, ToolBlockedResult
from agentsim.runtime.tool_matrix import builtin_seed_probe_steps
from agentsim.runtime.validator_stub import always_allow_validate
from agentsim.runtime.write_tools import SnapshotFn


Verdict = Literal["ALLOW", "BLOCK", "ERROR"]


@dataclass
class ToolCallSimulationRecord:
    """One simulated agent write attempt with policy outcome."""

    case_id: str
    tool_name: str
    parameters: dict[str, Any]
    verdict: Verdict
    executed: bool
    explanation: str | None = None
    unsat_core: list[str] | None = None
    error_message: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


from agentsim.runtime.write_tools import WriteToolExecutor


def _run_single_probe(
    *,
    case_id: str,
    tool_name: str,
    parameters: dict[str, Any],
    write_tools: WriteToolExecutor,
) -> ToolCallSimulationRecord:
    fn = getattr(write_tools, tool_name)
    try:
        out = fn(**dict(parameters))
    except Exception as exc:
        return ToolCallSimulationRecord(
            case_id=case_id,
            tool_name=tool_name,
            parameters=dict(parameters),
            verdict="ERROR",
            executed=False,
            error_message=str(exc),
        )
    if isinstance(out, ToolBlockedResult):
        return ToolCallSimulationRecord(
            case_id=case_id,
            tool_name=tool_name,
            parameters=dict(parameters),
            verdict="BLOCK",
            executed=False,
            explanation=out.reasons,
            unsat_core=out.unsat_core,
        )
    return ToolCallSimulationRecord(
        case_id=case_id,
        tool_name=tool_name,
        parameters=dict(parameters),
        verdict="ALLOW",
        executed=True,
    )


def run_write_tool_matrix(
    *,
    seed: Literal["builtin"] | Path | str = "builtin",
    customer_id: str = "C-001",
    channel: Channel = Channel.CHAT,
    use_builtin_z3_policy: bool = True,
    policy_smt2_path: Path | str | None = None,
    policy_smt2_text: str | None = None,
    validate_call: ValidateFn | None = None,
    build_snapshot: SnapshotFn | None = None,
    repeated_block_limit: int | None = None,
) -> list[ToolCallSimulationRecord]:
    """
    For each write tool, open a **new** seeded interaction and invoke one probe call.

    With ``use_builtin_z3_policy=True`` (default), validation uses
    :class:`~agentsim.runtime.z3_legality.Z3LegalityChecker` and policy text from
    ``policy_smt2_path`` / ``policy_smt2_text`` / bundled ``policy_v0.smt2``.

    With ``use_builtin_z3_policy=False``, pass ``validate_call`` (and optional
    ``build_snapshot``) to plug in any policy backend once your formalized model exists.
    """

    harness = ScenarioHarness()
    steps = builtin_seed_probe_steps()
    records: list[ToolCallSimulationRecord] = []

    for i, step in enumerate(steps):
        if step.get("op") != "write":
            continue
        tool = str(step["tool"])
        args = dict(step.get("args", {}))
        case_id = f"matrix-{i:03d}-{tool}"

        if use_builtin_z3_policy:
            ctx = harness.begin_scenario(
                seed=seed,
                customer_id=customer_id,
                channel=channel,
                use_builtin_z3_policy=True,
                policy_smt2_path=policy_smt2_path,
                policy_smt2_text=policy_smt2_text,
                repeated_block_limit=repeated_block_limit,
            )
        else:
            ctx = harness.begin_scenario(
                seed=seed,
                customer_id=customer_id,
                channel=channel,
                validate_call=validate_call or always_allow_validate,
                build_snapshot=build_snapshot,
                repeated_block_limit=repeated_block_limit,
            )

        records.append(
            _run_single_probe(
                case_id=case_id,
                tool_name=tool,
                parameters=args,
                write_tools=ctx.write_tools,
            ),
        )

    return records


def records_to_jsonl(records: list[ToolCallSimulationRecord]) -> str:
    lines = [json.dumps(r.to_json_dict(), sort_keys=True) for r in records]
    return "".join(line + "\n" for line in lines)
