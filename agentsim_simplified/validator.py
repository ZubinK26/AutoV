from __future__ import annotations

from agentsim_simplified.entities import Decision, StateBundle, ToolCall
from agentsim_simplified.simpl_checker import SimplPolicyChecker, SimplVerdict
from agentsim_simplified.simpl_scenario import RefundCallScenario


def validate_apply_refund(
    bundle: StateBundle | None,
    call: ToolCall,
    *,
    checker: SimplPolicyChecker | None = None,
) -> Decision:
    """Policy check for ``apply_refund`` tool call + optional ``StateBundle`` from lookup."""

    if call.tool_name != "apply_refund":
        msg = f"expected apply_refund, got {call.tool_name!r}"
        raise ValueError(msg)
    p = call.parameters
    refund_type = str(p["refund_type"])
    amount = int(p["amount_pence"])
    ch = checker or SimplPolicyChecker()
    scen = RefundCallScenario.from_bundle(bundle, refund_type=refund_type, refund_amount_pence=amount)
    d = ch.decide(scen)
    if d.verdict == SimplVerdict.PERMITTED:
        return Decision(True, [], "")
    if d.verdict == SimplVerdict.DENIED:
        return Decision(False, [], f"blocked: {d.detail}")
    # Conservative: ambiguous / inconsistent grounding does not automate allow
    return Decision(False, [], f"no proof of permission (ambiguous or inconsistent): {d.detail}")
