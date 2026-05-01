from __future__ import annotations

from typing import Any

from agentsim_simplified.agent import scenario_demo, validate_tool_schema
from agentsim_simplified.entities import RefundError, ToolCall
from agentsim_simplified.seed_data import load_db
from agentsim_simplified.simpl_checker import SimplPolicyChecker
from agentsim_simplified.tools import apply_refund, lookup_bundle
from agentsim_simplified.trace import TraceEntry, print_summary, print_trace
from agentsim_simplified.validator import validate_apply_refund


def execute_call(
    db: dict,
    call: ToolCall,
    step: int,
    description: str,
    *,
    checker: SimplPolicyChecker,
    last_bundle: dict[str, Any],
) -> TraceEntry:
    validate_tool_schema(call)
    if call.tool_name == "lookup_bundle":
        b = lookup_bundle(db, str(call.parameters["transaction_id"]))
        last_bundle.clear()
        if b is not None:
            last_bundle["_"] = b
        summ = "StateBundle returned" if b else "None (missing)"
        return TraceEntry(
            step=step,
            description=description,
            tool_name=call.tool_name,
            parameters=dict(call.parameters),
            decision="NA",
            unsat_core=[],
            explanation="",
            result_summary=summ,
        )
    bundle = last_bundle.get("_")
    dec = validate_apply_refund(bundle, call, checker=checker)
    if dec.allow:
        res = apply_refund(db, call, checker=checker)
        if isinstance(res, RefundError):
            return TraceEntry(
                step=step,
                description=description,
                tool_name=call.tool_name,
                parameters=dict(call.parameters),
                decision="BLOCK",
                unsat_core=list(res.rule_ids),
                explanation=res.reasons,
                result_summary="unexpected block after permit",
            )
        return TraceEntry(
            step=step,
            description=description,
            tool_name=call.tool_name,
            parameters=dict(call.parameters),
            decision="ALLOW",
            unsat_core=[],
            explanation="",
            result_summary=f"refund {res.refund_id} created",
        )
    return TraceEntry(
        step=step,
        description=description,
        tool_name=call.tool_name,
        parameters=dict(call.parameters),
        decision="BLOCK",
        unsat_core=dec.unsat_core,
        explanation=dec.explanation,
        result_summary="blocked",
    )


def run_scenario(
    scenario: list[tuple[str, ToolCall]] | None = None,
    *,
    checker: SimplPolicyChecker | None = None,
) -> list[TraceEntry]:
    db = load_db()
    ch = checker or SimplPolicyChecker()
    last_bundle: dict[str, Any] = {}
    trace: list[TraceEntry] = []
    scen = scenario if scenario is not None else scenario_demo
    for step, (description, call) in enumerate(scen, start=1):
        trace.append(execute_call(db, call, step, description, checker=ch, last_bundle=last_bundle))
    print_trace(trace)
    print_summary(trace)
    return trace


def main() -> int:
    run_scenario()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
