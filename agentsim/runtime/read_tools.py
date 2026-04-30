from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from agentsim.runtime.audit import append_audit
from agentsim.runtime.clock import NowFn
from agentsim.runtime.models import (
    Account,
    AuditDecision,
    AuditLogEntry,
    Card,
    Customer,
    Dispute,
    FraudReport,
    Interaction,
    Refund,
    Restriction,
    ToolCall,
    Transaction,
)


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _row_customer(row: sqlite3.Row) -> Customer:
    return Customer.model_validate(
        {
            "customer_id": row["customer_id"],
            "kyc_status": row["kyc_status"],
            "account_tier": row["account_tier"],
            "vulnerable_flag": bool(row["vulnerable_flag"]),
            "pep_flag": bool(row["pep_flag"]),
            "sanctions_flag": bool(row["sanctions_flag"]),
            "joint_account": bool(row["joint_account"]),
            "account_open_date": row["account_open_date"],
            "dispute_count_last_12m": row["dispute_count_last_12m"],
            "prior_goodwill_credits_last_12m_amount": row["prior_goodwill_credits_last_12m_amount"],
        },
    )


def _row_account(row: sqlite3.Row) -> Account:
    return Account.model_validate(
        {
            "account_id": row["account_id"],
            "customer_id": row["customer_id"],
            "balance_pence": row["balance_pence"],
            "available_balance_pence": row["available_balance_pence"],
            "currency": row["currency"],
            "account_status": row["account_status"],
            "restriction_reasons": json.loads(row["restriction_reasons_json"]),
        },
    )


def _row_transaction(row: sqlite3.Row) -> Transaction:
    return Transaction(
        transaction_id=row["transaction_id"],
        account_id=row["account_id"],
        card_id=row["card_id"],
        merchant_name=row["merchant_name"],
        merchant_category=row["merchant_category"],
        amount_pence=row["amount_pence"],
        currency=row["currency"],
        transaction_date=_parse_dt(row["transaction_date"]),
        posted_date=_parse_dt(row["posted_date"]),
        status=row["status"],
        is_section75_eligible=bool(row["is_section75_eligible"]),
        chargeback_window_days=row["chargeback_window_days"],
    )


def _row_dispute(row: sqlite3.Row) -> Dispute:
    docs = json.loads(row["evidence_documents_json"])
    stmt = row["customer_statement"] if "customer_statement" in row.keys() else ""
    return Dispute(
        dispute_id=row["dispute_id"],
        transaction_id=row["transaction_id"],
        customer_id=row["customer_id"],
        dispute_type=row["dispute_type"],
        dispute_status=row["dispute_status"],
        opened_date=_parse_dt(row["opened_date"]),
        evidence_documents=docs,
        outcome_amount_pence=row["outcome_amount_pence"],
        customer_statement=str(stmt) if stmt is not None else "",
    )


def _row_card(row: sqlite3.Row) -> Card:
    return Card.model_validate(
        {
            "card_id": row["card_id"],
            "account_id": row["account_id"],
            "card_status": row["card_status"],
            "card_type": row["card_type"],
        },
    )


def _row_refund(row: sqlite3.Row) -> Refund:
    return Refund.model_validate(
        {
            "refund_id": row["refund_id"],
            "transaction_id": row["transaction_id"],
            "customer_id": row["customer_id"],
            "refund_type": row["refund_type"],
            "amount_pence": row["amount_pence"],
            "requires_approval": bool(row["requires_approval"]),
            "approval_status": row["approval_status"],
            "created_date": row["created_date"],
        },
    )


def _row_interaction(row: sqlite3.Row) -> Interaction:
    actions_raw = json.loads(row["actions_taken_json"])
    actions = [ToolCall.model_validate(a) for a in actions_raw]
    return Interaction(
        interaction_id=row["interaction_id"],
        customer_id=row["customer_id"],
        channel=row["channel"],
        started_at=_parse_dt(row["started_at"]),
        actions_taken=actions,
        escalated_to_human=bool(row["escalated_to_human"]),
    )


def _row_restriction(row: sqlite3.Row) -> Restriction:
    lift = row["lift_eligible_after"]
    return Restriction(
        restriction_id=row["restriction_id"],
        account_id=row["account_id"],
        restriction_type=row["restriction_type"],
        applied_date=_parse_dt(row["applied_date"]),
        lift_eligible_after=_parse_dt(lift) if lift else None,
        requires_human_to_lift=bool(row["requires_human_to_lift"]),
    )


def _row_fraud_report(row: sqlite3.Row) -> FraudReport:
    tx_ids = json.loads(row["transaction_ids_json"])
    return FraudReport(
        fraud_report_id=row["fraud_report_id"],
        customer_id=row["customer_id"],
        transaction_ids=tx_ids,
        fraud_type=row["fraud_type"],
        report_status=row["report_status"],
        reported_date=_parse_dt(row["reported_date"]),
    )


class ReadToolExecutor:
    """Nine read tools from agentsim/01 — each appends an audit row with decision NA."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        interaction_id: str,
        policy_version: str,
        clock: NowFn,
    ) -> None:
        self.conn = conn
        self.interaction_id = interaction_id
        self.policy_version = policy_version
        self.clock = clock

    def _audit(self, tool_name: str, parameters: dict) -> None:
        append_audit(
            self.conn,
            AuditLogEntry(
                interaction_id=self.interaction_id,
                timestamp=self.clock(),
                tool_name=tool_name,
                parameters=parameters,
                decision=AuditDecision.NA,
                unsat_core=None,
                explanation=None,
                policy_version=self.policy_version,
                rules_consulted=[],
            ),
        )

    def lookup_customer(self, customer_id: str) -> Customer | None:
        cur = self.conn.execute(
            "SELECT * FROM customer WHERE customer_id = ?",
            (customer_id,),
        )
        row = cur.fetchone()
        self._audit("lookup_customer", {"customer_id": customer_id})
        return _row_customer(row) if row else None

    def lookup_account(self, account_id: str) -> Account | None:
        cur = self.conn.execute(
            "SELECT * FROM account WHERE account_id = ?",
            (account_id,),
        )
        row = cur.fetchone()
        self._audit("lookup_account", {"account_id": account_id})
        return _row_account(row) if row else None

    def lookup_transaction(self, transaction_id: str) -> Transaction | None:
        cur = self.conn.execute(
            "SELECT * FROM transaction_row WHERE transaction_id = ?",
            (transaction_id,),
        )
        row = cur.fetchone()
        self._audit("lookup_transaction", {"transaction_id": transaction_id})
        return _row_transaction(row) if row else None

    def list_recent_transactions(self, account_id: str, limit: int) -> list[Transaction]:
        cur = self.conn.execute(
            """
            SELECT * FROM transaction_row
            WHERE account_id = ?
            ORDER BY transaction_date DESC
            LIMIT ?
            """,
            (account_id, limit),
        )
        rows = cur.fetchall()
        out = [_row_transaction(r) for r in rows]
        self._audit(
            "list_recent_transactions",
            {"account_id": account_id, "limit": limit},
        )
        return out

    def lookup_dispute(self, dispute_id: str) -> Dispute | None:
        cur = self.conn.execute(
            "SELECT * FROM dispute WHERE dispute_id = ?",
            (dispute_id,),
        )
        row = cur.fetchone()
        self._audit("lookup_dispute", {"dispute_id": dispute_id})
        return _row_dispute(row) if row else None

    def list_customer_disputes(self, customer_id: str, limit: int) -> list[Dispute]:
        cur = self.conn.execute(
            """
            SELECT * FROM dispute
            WHERE customer_id = ?
            ORDER BY opened_date DESC
            LIMIT ?
            """,
            (customer_id, limit),
        )
        rows = cur.fetchall()
        out = [_row_dispute(r) for r in rows]
        self._audit(
            "list_customer_disputes",
            {"customer_id": customer_id, "limit": limit},
        )
        return out

    def check_account_restrictions(self, account_id: str) -> list[Restriction]:
        cur = self.conn.execute(
            "SELECT * FROM restriction WHERE account_id = ? ORDER BY applied_date DESC",
            (account_id,),
        )
        rows = cur.fetchall()
        out = [_row_restriction(r) for r in rows]
        self._audit("check_account_restrictions", {"account_id": account_id})
        return out

    def lookup_fraud_report(self, fraud_report_id: str) -> FraudReport | None:
        cur = self.conn.execute(
            "SELECT * FROM fraud_report WHERE fraud_report_id = ?",
            (fraud_report_id,),
        )
        row = cur.fetchone()
        self._audit("lookup_fraud_report", {"fraud_report_id": fraud_report_id})
        return _row_fraud_report(row) if row else None

    def check_section_75_eligibility(self, transaction_id: str) -> bool:
        cur = self.conn.execute(
            """
            SELECT is_section75_eligible FROM transaction_row WHERE transaction_id = ?
            """,
            (transaction_id,),
        )
        row = cur.fetchone()
        eligible = bool(row["is_section75_eligible"]) if row else False
        self._audit(
            "check_section_75_eligibility",
            {"transaction_id": transaction_id},
        )
        return eligible
