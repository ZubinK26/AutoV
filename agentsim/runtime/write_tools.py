from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from typing import Any

from agentsim.runtime.audit import append_audit
from agentsim.runtime.clock import NowFn
from agentsim.runtime.models import (
    AuditDecision,
    AuditLogEntry,
    Card,
    ConsumerDutyAssessment,
    Decision,
    Dispute,
    DisputeType,
    FraudReport,
    FraudType,
    Interaction,
    Refund,
    RefundType,
    Restriction,
    RestrictionType,
    ToolBlockedResult,
    ToolCall,
)
from agentsim.runtime import write_ops

ValidateFn = Callable[[ToolCall, dict[str, Any]], Decision]
SnapshotFn = Callable[[ToolCall], dict[str, Any]]


class WriteToolExecutor:
    """Write tools (agentsim/01): validate_call → execute → audit ALLOW/BLOCK."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        interaction_id: str,
        policy_version: str,
        clock: NowFn,
        validate_call: ValidateFn,
        build_snapshot: SnapshotFn | None = None,
        repeated_block_limit: int | None = None,
    ) -> None:
        self.conn = conn
        self.interaction_id = interaction_id
        self.policy_version = policy_version
        self.clock = clock
        self.validate_call = validate_call
        self.build_snapshot = build_snapshot or (lambda _c: {})
        self._repeated_block_limit = repeated_block_limit
        self._block_fingerprint: str | None = None
        self._block_streak = 0

    def _audit(
        self,
        *,
        tool_name: str,
        parameters: dict[str, Any],
        decision: AuditDecision,
        unsat_core: list[str] | None = None,
        explanation: str | None = None,
    ) -> None:
        append_audit(
            self.conn,
            AuditLogEntry(
                interaction_id=self.interaction_id,
                timestamp=self.clock(),
                tool_name=tool_name,
                parameters=parameters,
                decision=decision,
                unsat_core=unsat_core,
                explanation=explanation,
                policy_version=self.policy_version,
                rules_consulted=[],
            ),
        )

    def _run(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        execute: Callable[[], Any],
    ) -> Any:
        call = ToolCall(
            tool_name=tool_name,
            parameters=parameters,
            proposed_at=self.clock(),
            interaction_id=self.interaction_id,
        )
        decision = self.validate_call(call, self.build_snapshot(call))
        if not decision.allow:
            self._audit(
                tool_name=tool_name,
                parameters=parameters,
                decision=AuditDecision.BLOCK,
                unsat_core=decision.unsat_core,
                explanation=decision.explanation or "blocked",
            )
            self._on_blocked_call(call)
            return ToolBlockedResult(
                reasons=decision.explanation or "blocked",
                unsat_core=decision.unsat_core,
            )
        self._block_fingerprint = None
        self._block_streak = 0
        result = execute()
        self._audit(
            tool_name=tool_name,
            parameters=parameters,
            decision=AuditDecision.ALLOW,
        )
        return result

    def _on_blocked_call(self, call: ToolCall) -> None:
        fp = json.dumps({"tool": call.tool_name, "parameters": call.parameters}, sort_keys=True)
        if fp == self._block_fingerprint:
            self._block_streak += 1
        else:
            self._block_fingerprint = fp
            self._block_streak = 1
        lim = self._repeated_block_limit
        if lim is not None and self._block_streak >= lim:
            self._force_escalate_guard(call)
            self._block_fingerprint = None
            self._block_streak = 0

    def _force_escalate_guard(self, call: ToolCall) -> None:
        now = self.clock()
        write_ops.escalate_to_human(
            self.conn,
            interaction_id=self.interaction_id,
            reason=(
                f"Auto-escalation after {self._repeated_block_limit} consecutive "
                f"blocked attempts for {call.tool_name}"
            ),
            urgency="HIGH",
            at=now,
        )
        self._audit(
            tool_name="force_escalation_guard",
            parameters={
                "triggering_tool": call.tool_name,
                "consecutive_blocks": self._repeated_block_limit,
            },
            decision=AuditDecision.ALLOW,
        )

    def initiate_dispute(
        self,
        transaction_id: str,
        dispute_type: str | DisputeType,
        customer_statement: str,
    ) -> Dispute | ToolBlockedResult:
        dt = DisputeType(dispute_type) if not isinstance(dispute_type, DisputeType) else dispute_type
        params: dict[str, Any] = {
            "transaction_id": transaction_id,
            "dispute_type": dt.value,
            "customer_statement": customer_statement,
        }
        now = self.clock()

        def go() -> Dispute:
            return write_ops.initiate_dispute(
                self.conn,
                transaction_id=transaction_id,
                dispute_type=dt,
                customer_statement=customer_statement,
                opened_at=now,
            )

        return self._run("initiate_dispute", params, go)

    def cancel_dispute(self, dispute_id: str, reason: str) -> Dispute | ToolBlockedResult:
        params = {"dispute_id": dispute_id, "reason": reason}
        now = self.clock()

        def go() -> Dispute:
            return write_ops.cancel_dispute(
                self.conn,
                dispute_id=dispute_id,
                reason=reason,
                at=now,
            )

        return self._run("cancel_dispute", params, go)

    def apply_refund(
        self,
        transaction_id: str,
        amount_pence: int,
        refund_type: str | RefundType,
        reason: str,
    ) -> Refund | ToolBlockedResult:
        rt = RefundType(refund_type) if not isinstance(refund_type, RefundType) else refund_type
        params: dict[str, Any] = {
            "transaction_id": transaction_id,
            "amount_pence": amount_pence,
            "refund_type": rt.value,
            "reason": reason,
        }
        now = self.clock()

        def go() -> Refund:
            return write_ops.apply_refund(
                self.conn,
                transaction_id=transaction_id,
                amount_pence=amount_pence,
                refund_type=rt,
                reason=reason,
                created_at=now,
            )

        return self._run("apply_refund", params, go)

    def apply_goodwill_credit(
        self,
        customer_id: str,
        amount_pence: int,
        reason: str,
    ) -> Refund | ToolBlockedResult:
        params = {
            "customer_id": customer_id,
            "amount_pence": amount_pence,
            "reason": reason,
        }
        now = self.clock()

        def go() -> Refund:
            return write_ops.apply_goodwill_credit(
                self.conn,
                customer_id=customer_id,
                amount_pence=amount_pence,
                reason=reason,
                created_at=now,
            )

        return self._run("apply_goodwill_credit", params, go)

    def apply_fee_reversal(
        self,
        transaction_id: str,
        reason: str,
    ) -> Refund | ToolBlockedResult:
        params = {"transaction_id": transaction_id, "reason": reason}
        now = self.clock()

        def go() -> Refund:
            return write_ops.apply_fee_reversal(
                self.conn,
                transaction_id=transaction_id,
                reason=reason,
                created_at=now,
            )

        return self._run("apply_fee_reversal", params, go)

    def freeze_card(self, card_id: str, reason: str) -> Card | ToolBlockedResult:
        params = {"card_id": card_id, "reason": reason}
        now = self.clock()

        def go() -> Card:
            return write_ops.freeze_card(self.conn, card_id=card_id, reason=reason, at=now)

        return self._run("freeze_card", params, go)

    def unfreeze_card(self, card_id: str, reason: str) -> Card | ToolBlockedResult:
        params = {"card_id": card_id, "reason": reason}
        now = self.clock()

        def go() -> Card:
            return write_ops.unfreeze_card(self.conn, card_id=card_id, reason=reason, at=now)

        return self._run("unfreeze_card", params, go)

    def apply_account_restriction(
        self,
        account_id: str,
        restriction_type: str | RestrictionType,
        reason: str,
    ) -> Restriction | ToolBlockedResult:
        rt = (
            RestrictionType(restriction_type)
            if not isinstance(restriction_type, RestrictionType)
            else restriction_type
        )
        params: dict[str, Any] = {
            "account_id": account_id,
            "restriction_type": rt.value,
            "reason": reason,
        }
        now = self.clock()

        def go() -> Restriction:
            return write_ops.apply_account_restriction(
                self.conn,
                account_id=account_id,
                restriction_type=rt,
                reason=reason,
                applied_at=now,
            )

        return self._run("apply_account_restriction", params, go)

    def lift_account_restriction(
        self,
        restriction_id: str,
        reason: str,
    ) -> Restriction | ToolBlockedResult:
        params = {"restriction_id": restriction_id, "reason": reason}
        now = self.clock()

        def go() -> Restriction:
            return write_ops.lift_account_restriction(
                self.conn,
                restriction_id=restriction_id,
                reason=reason,
                at=now,
            )

        return self._run("lift_account_restriction", params, go)

    def report_fraud(
        self,
        customer_id: str,
        transaction_ids: list[str],
        fraud_type: str | FraudType,
    ) -> FraudReport | ToolBlockedResult:
        ft = FraudType(fraud_type) if not isinstance(fraud_type, FraudType) else fraud_type
        params: dict[str, Any] = {
            "customer_id": customer_id,
            "transaction_ids": transaction_ids,
            "fraud_type": ft.value,
        }
        now = self.clock()

        def go() -> FraudReport:
            return write_ops.report_fraud(
                self.conn,
                customer_id=customer_id,
                transaction_ids=transaction_ids,
                fraud_type=ft,
                reported_at=now,
            )

        return self._run("report_fraud", params, go)

    def escalate_to_human(self, reason: str, urgency: str) -> Interaction | ToolBlockedResult:
        params = {"reason": reason, "urgency": urgency}
        now = self.clock()

        def go() -> Interaction:
            return write_ops.escalate_to_human(
                self.conn,
                interaction_id=self.interaction_id,
                reason=reason,
                urgency=urgency,
                at=now,
            )

        return self._run("escalate_to_human", params, go)

    def request_documentation(
        self,
        customer_id: str,
        document_type: str,
        deadline: str,
    ) -> None | ToolBlockedResult:
        params = {
            "customer_id": customer_id,
            "document_type": document_type,
            "deadline": deadline,
        }
        now = self.clock()

        def go() -> None:
            write_ops.request_documentation(
                self.conn,
                interaction_id=self.interaction_id,
                customer_id=customer_id,
                document_type=document_type,
                deadline=deadline,
                created_at=now,
            )

        return self._run("request_documentation", params, go)

    def send_customer_message(
        self,
        customer_id: str,
        message_text: str,
        message_category: str,
    ) -> None | ToolBlockedResult:
        params = {
            "customer_id": customer_id,
            "message_text": message_text,
            "message_category": message_category,
        }
        now = self.clock()

        def go() -> None:
            write_ops.send_customer_message(
                self.conn,
                interaction_id=self.interaction_id,
                customer_id=customer_id,
                message_text=message_text,
                message_category=message_category,
                created_at=now,
            )

        return self._run("send_customer_message", params, go)

    def log_consumer_duty_assessment(
        self,
        customer_id: str,
        vulnerability_indicators: list[str],
        checks: dict[str, bool],
    ) -> ConsumerDutyAssessment | ToolBlockedResult:
        fv = bool(checks.get("fair_value_check_passed", False))
        cc = bool(checks.get("clear_communication_check_passed", False))
        params: dict[str, Any] = {
            "customer_id": customer_id,
            "vulnerability_indicators": vulnerability_indicators,
            "checks": checks,
        }
        now = self.clock()

        def go() -> ConsumerDutyAssessment:
            return write_ops.log_consumer_duty_assessment(
                self.conn,
                interaction_id=self.interaction_id,
                customer_id=customer_id,
                vulnerability_indicators=vulnerability_indicators,
                fair_value_check_passed=fv,
                clear_communication_check_passed=cc,
                assessment_at=now,
            )

        return self._run("log_consumer_duty_assessment", params, go)
