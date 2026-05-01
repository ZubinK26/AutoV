from __future__ import annotations

from agentsim_simplified.entities import SchemaError, ToolCall


def _validate_lookup(call: ToolCall) -> None:
    if call.parameters.keys() != {"transaction_id"}:
        raise SchemaError(f"lookup_bundle expects transaction_id only, got {call.parameters!r}")


def _validate_apply_refund_shape(call: ToolCall) -> None:
    need = {"transaction_id", "amount_pence", "refund_type", "reason"}
    if set(call.parameters.keys()) != need:
        raise SchemaError(f"apply_refund expects keys {sorted(need)}, got {sorted(call.parameters.keys())}")


def validate_tool_schema(call: ToolCall) -> None:
    if call.tool_name == "lookup_bundle":
        _validate_lookup(call)
    elif call.tool_name == "apply_refund":
        _validate_apply_refund_shape(call)
    else:
        msg = f"unknown tool {call.tool_name!r}"
        raise SchemaError(msg)


# (description, ToolCall) per 02_agent_interactions_simpl.md
scenario_demo: list[tuple[str, ToolCall]] = [
    ("Look up a clean transaction for C-001", ToolCall("lookup_bundle", {"transaction_id": "T-001"})),
    (
        "Issue a £30 merchant refund on T-001 — should ALLOW",
        ToolCall(
            "apply_refund",
            {
                "transaction_id": "T-001",
                "amount_pence": 3000,
                "refund_type": "MERCHANT_REFUND",
                "reason": "merchant agreed to refund partial amount",
            },
        ),
    ),
    ("Look up T-004 (customer has FAILED KYC)", ToolCall("lookup_bundle", {"transaction_id": "T-004"})),
    (
        "Try a refund on T-004 — should BLOCK on KYC",
        ToolCall(
            "apply_refund",
            {
                "transaction_id": "T-004",
                "amount_pence": 2000,
                "refund_type": "MERCHANT_REFUND",
                "reason": "support request",
            },
        ),
    ),
    ("Look up T-005 (account has sanctions block)", ToolCall("lookup_bundle", {"transaction_id": "T-005"})),
    (
        "Try a refund on T-005 — should BLOCK on sanctions",
        ToolCall(
            "apply_refund",
            {
                "transaction_id": "T-005",
                "amount_pence": 3000,
                "refund_type": "MERCHANT_REFUND",
                "reason": "support request",
            },
        ),
    ),
    ("Look up T-003 (customer near goodwill cap)", ToolCall("lookup_bundle", {"transaction_id": "T-003"})),
    (
        "Try a £10 goodwill credit — should BLOCK on rolling cap",
        ToolCall(
            "apply_refund",
            {
                "transaction_id": "T-003",
                "amount_pence": 1000,
                "refund_type": "GOODWILL_CREDIT",
                "reason": "service issue",
            },
        ),
    ),
    ("Look up T-006 (8k transaction)", ToolCall("lookup_bundle", {"transaction_id": "T-006"})),
    (
        "Try refund > txn amount on T-006 — should BLOCK",
        ToolCall(
            "apply_refund",
            {
                "transaction_id": "T-006",
                "amount_pence": 10000,
                "refund_type": "MERCHANT_REFUND",
                "reason": "support overrefunded",
            },
        ),
    ),
]
