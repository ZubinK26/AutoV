"""
One probe call per write tool using :mod:`agentsim.runtime.data.seed_minimal` IDs.

Each probe is meant to run on a **fresh** seeded DB so tools stay independent.
"""

from __future__ import annotations

from typing import Any

from agentsim.runtime.scenario_runner import WriteStep
from agentsim.runtime.write_registry import WRITE_TOOL_IDS

# Arguments valid for builtin seed (see seed_minimal.json).
_BUILTIN_PROBE_ARGS: dict[str, dict[str, Any]] = {
    "initiate_dispute": {
        "transaction_id": "T-002",
        "dispute_type": "UNAUTHORIZED",
        "customer_statement": "Simulation probe: unrecognized charge.",
    },
    "cancel_dispute": {
        "dispute_id": "D-001",
        "reason": "Simulation probe: customer withdrew.",
    },
    "apply_refund": {
        "transaction_id": "T-002",
        "amount_pence": 50,
        "refund_type": "MERCHANT_REFUND",
        "reason": "Simulation probe refund.",
    },
    "apply_goodwill_credit": {
        "customer_id": "C-001",
        "amount_pence": 500,
        "reason": "Simulation probe goodwill.",
    },
    "apply_fee_reversal": {
        "transaction_id": "T-002",
        "reason": "Simulation probe fee waiver.",
    },
    "freeze_card": {
        "card_id": "K-001",
        "reason": "Simulation probe temporary freeze.",
    },
    "unfreeze_card": {
        "card_id": "K-001",
        "reason": "Simulation probe unfreeze.",
    },
    "apply_account_restriction": {
        "account_id": "A-001",
        "restriction_type": "COMPLIANCE_REVIEW",
        "reason": "Simulation probe restriction.",
    },
    "lift_account_restriction": {
        "restriction_id": "R-001",
        "reason": "Simulation probe lift.",
    },
    "report_fraud": {
        "customer_id": "C-001",
        "transaction_ids": ["T-002"],
        "fraud_type": "APP_FRAUD",
    },
    "escalate_to_human": {
        "reason": "Simulation probe escalation.",
        "urgency": "MEDIUM",
    },
    "request_documentation": {
        "customer_id": "C-001",
        "document_type": "PROOF_OF_ADDRESS",
        "deadline": "2026-12-31",
    },
    "send_customer_message": {
        "customer_id": "C-001",
        "message_text": "Simulation probe outbound message.",
        "message_category": "UPDATE",
    },
    "log_consumer_duty_assessment": {
        "customer_id": "C-001",
        "vulnerability_indicators": ["simulation_probe"],
        "checks": {
            "fair_value_check_passed": True,
            "clear_communication_check_passed": True,
        },
    },
}


def _ensure_matrix_complete() -> None:
    if frozenset(_BUILTIN_PROBE_ARGS) != frozenset(WRITE_TOOL_IDS):
        diff = frozenset(_BUILTIN_PROBE_ARGS) ^ frozenset(WRITE_TOOL_IDS)
        msg = f"builtin probe args mismatch for tools: {diff}"
        raise RuntimeError(msg)


_ensure_matrix_complete()


def builtin_seed_probe_steps() -> list[WriteStep]:
    """Ordered probe steps: one write per tool, seed-compatible arguments."""

    out: list[WriteStep] = []
    for tool in WRITE_TOOL_IDS:
        out.append(
            {
                "op": "write",
                "tool": tool,
                "args": dict(_BUILTIN_PROBE_ARGS[tool]),
            },
        )
    return out


def builtin_probe_args_for(tool_name: str) -> dict[str, Any]:
    """Arguments for a single-tool probe on a fresh builtin seed DB."""

    return dict(_BUILTIN_PROBE_ARGS[tool_name])
