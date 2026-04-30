"""Canonical names for agent write tools (single source for matrix, metrics, audits)."""

from __future__ import annotations

# Stable iteration order for simulation matrices and reports.
WRITE_TOOL_IDS: tuple[str, ...] = (
    "apply_account_restriction",
    "apply_fee_reversal",
    "apply_goodwill_credit",
    "apply_refund",
    "cancel_dispute",
    "escalate_to_human",
    "freeze_card",
    "initiate_dispute",
    "lift_account_restriction",
    "log_consumer_duty_assessment",
    "report_fraud",
    "request_documentation",
    "send_customer_message",
    "unfreeze_card",
)

WRITE_TOOL_NAMES: frozenset[str] = frozenset(WRITE_TOOL_IDS)
