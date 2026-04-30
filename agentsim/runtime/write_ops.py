from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from decimal import Decimal

from agentsim.runtime.models import (
    AccountStatus,
    ApprovalStatus,
    Card,
    CardStatus,
    ConsumerDutyAssessment,
    Dispute,
    DisputeStatus,
    DisputeType,
    FraudReport,
    FraudReportStatus,
    FraudType,
    Interaction,
    Refund,
    RefundType,
    Restriction,
    RestrictionType,
    TransactionStatus,
)
from agentsim.runtime.read_tools import (
    _row_card,
    _row_dispute,
    _row_fraud_report,
    _row_interaction,
    _row_refund,
    _row_restriction,
)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _credit_account_pence(conn: sqlite3.Connection, account_id: str, delta_pence: int) -> None:
    conn.execute(
        """
        UPDATE account SET
            balance_pence = balance_pence + ?,
            available_balance_pence = available_balance_pence + ?
        WHERE account_id = ?
        """,
        (delta_pence, delta_pence, account_id),
    )


def initiate_dispute(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    dispute_type: DisputeType,
    customer_statement: str,
    opened_at: datetime,
) -> Dispute:
    cur = conn.execute(
        """
        SELECT t.account_id, a.customer_id FROM transaction_row t
        JOIN account a ON a.account_id = t.account_id
        WHERE t.transaction_id = ?
        """,
        (transaction_id,),
    )
    row = cur.fetchone()
    if row is None:
        msg = f"transaction not found: {transaction_id}"
        raise ValueError(msg)
    customer_id = row["customer_id"]

    dispute_id = _new_id("D")
    conn.execute(
        """
        INSERT INTO dispute (
            dispute_id, transaction_id, customer_id, dispute_type, dispute_status,
            opened_date, evidence_documents_json, outcome_amount_pence, customer_statement
        ) VALUES (?, ?, ?, ?, ?, ?, '[]', NULL, ?)
        """,
        (
            dispute_id,
            transaction_id,
            customer_id,
            dispute_type.value if isinstance(dispute_type, DisputeType) else dispute_type,
            DisputeStatus.OPEN.value,
            opened_at.isoformat(),
            customer_statement,
        ),
    )
    conn.execute(
        """
        UPDATE transaction_row SET status = ? WHERE transaction_id = ?
        """,
        (TransactionStatus.DISPUTED.value, transaction_id),
    )
    conn.execute(
        """
        UPDATE customer SET dispute_count_last_12m = dispute_count_last_12m + 1
        WHERE customer_id = ?
        """,
        (customer_id,),
    )
    conn.commit()
    out = conn.execute("SELECT * FROM dispute WHERE dispute_id = ?", (dispute_id,)).fetchone()
    assert out is not None
    return _row_dispute(out)


def cancel_dispute(
    conn: sqlite3.Connection,
    *,
    dispute_id: str,
    reason: str,
    at: datetime,
) -> Dispute:
    _ = reason  # reserved for policy / audit templates
    conn.execute(
        """
        UPDATE dispute SET dispute_status = ? WHERE dispute_id = ?
        """,
        (DisputeStatus.WITHDRAWN.value, dispute_id),
    )
    conn.commit()
    out = conn.execute("SELECT * FROM dispute WHERE dispute_id = ?", (dispute_id,)).fetchone()
    if out is None:
        msg = f"dispute not found: {dispute_id}"
        raise ValueError(msg)
    return _row_dispute(out)


def _insert_refund_and_credit(
    conn: sqlite3.Connection,
    *,
    transaction_id: str | None,
    customer_id: str,
    refund_type: RefundType,
    amount_pence: int,
    account_id: str,
    created_at: datetime,
) -> Refund:
    requires = amount_pence > 50_000
    approval = ApprovalStatus.PENDING.value if requires else ApprovalStatus.AUTO_APPROVED.value
    refund_id = _new_id("RF")
    conn.execute(
        """
        INSERT INTO refund (
            refund_id, transaction_id, customer_id, refund_type, amount_pence,
            requires_approval, approval_status, created_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            refund_id,
            transaction_id,
            customer_id,
            refund_type.value if isinstance(refund_type, RefundType) else refund_type,
            amount_pence,
            int(requires),
            approval,
            created_at.isoformat(),
        ),
    )
    _credit_account_pence(conn, account_id, amount_pence)
    conn.commit()
    out = conn.execute("SELECT * FROM refund WHERE refund_id = ?", (refund_id,)).fetchone()
    assert out is not None
    return _row_refund(out)


def apply_refund(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    amount_pence: int,
    refund_type: RefundType,
    reason: str,
    created_at: datetime,
) -> Refund:
    _ = reason
    cur = conn.execute(
        """
        SELECT t.account_id, a.customer_id FROM transaction_row t
        JOIN account a ON a.account_id = t.account_id
        WHERE t.transaction_id = ?
        """,
        (transaction_id,),
    )
    row = cur.fetchone()
    if row is None:
        msg = f"transaction not found: {transaction_id}"
        raise ValueError(msg)
    return _insert_refund_and_credit(
        conn,
        transaction_id=transaction_id,
        customer_id=row["customer_id"],
        refund_type=refund_type,
        amount_pence=amount_pence,
        account_id=row["account_id"],
        created_at=created_at,
    )


def apply_goodwill_credit(
    conn: sqlite3.Connection,
    *,
    customer_id: str,
    amount_pence: int,
    reason: str,
    created_at: datetime,
) -> Refund:
    _ = reason
    cur = conn.execute(
        "SELECT account_id FROM account WHERE customer_id = ? LIMIT 1",
        (customer_id,),
    )
    row = cur.fetchone()
    if row is None:
        msg = f"no account for customer: {customer_id}"
        raise ValueError(msg)
    account_id = row["account_id"]
    ref = _insert_refund_and_credit(
        conn,
        transaction_id=None,
        customer_id=customer_id,
        refund_type=RefundType.GOODWILL_CREDIT,
        amount_pence=amount_pence,
        account_id=account_id,
        created_at=created_at,
    )
    cur2 = conn.execute(
        "SELECT prior_goodwill_credits_last_12m_amount FROM customer WHERE customer_id = ?",
        (customer_id,),
    )
    c2 = cur2.fetchone()
    if c2 is None:
        return ref
    prev = Decimal(str(c2["prior_goodwill_credits_last_12m_amount"]))
    prev += Decimal(amount_pence) / 100
    conn.execute(
        """
        UPDATE customer SET prior_goodwill_credits_last_12m_amount = ? WHERE customer_id = ?
        """,
        (str(prev), customer_id),
    )
    conn.commit()
    return ref


def apply_fee_reversal(
    conn: sqlite3.Connection,
    *,
    transaction_id: str,
    reason: str,
    created_at: datetime,
) -> Refund:
    _ = reason
    cur = conn.execute(
        """
        SELECT t.amount_pence, t.account_id, a.customer_id
        FROM transaction_row t
        JOIN account a ON a.account_id = t.account_id
        WHERE t.transaction_id = ?
        """,
        (transaction_id,),
    )
    row = cur.fetchone()
    if row is None:
        msg = f"transaction not found: {transaction_id}"
        raise ValueError(msg)
    amount = abs(int(row["amount_pence"]))
    return _insert_refund_and_credit(
        conn,
        transaction_id=transaction_id,
        customer_id=row["customer_id"],
        refund_type=RefundType.FEE_REVERSAL,
        amount_pence=amount,
        account_id=row["account_id"],
        created_at=created_at,
    )


def freeze_card(
    conn: sqlite3.Connection,
    *,
    card_id: str,
    reason: str,
    at: datetime,
) -> Card:
    _ = reason, at
    conn.execute(
        "UPDATE card SET card_status = ? WHERE card_id = ?",
        (CardStatus.FROZEN.value, card_id),
    )
    conn.commit()
    out = conn.execute("SELECT * FROM card WHERE card_id = ?", (card_id,)).fetchone()
    if out is None:
        msg = f"card not found: {card_id}"
        raise ValueError(msg)
    return _row_card(out)


def unfreeze_card(
    conn: sqlite3.Connection,
    *,
    card_id: str,
    reason: str,
    at: datetime,
) -> Card:
    _ = reason, at
    conn.execute(
        "UPDATE card SET card_status = ? WHERE card_id = ?",
        (CardStatus.ACTIVE.value, card_id),
    )
    conn.commit()
    out = conn.execute("SELECT * FROM card WHERE card_id = ?", (card_id,)).fetchone()
    if out is None:
        msg = f"card not found: {card_id}"
        raise ValueError(msg)
    return _row_card(out)


def _sync_account_restrictions(conn: sqlite3.Connection, account_id: str) -> None:
    cur = conn.execute(
        "SELECT restriction_type FROM restriction WHERE account_id = ?",
        (account_id,),
    )
    types = [r["restriction_type"] for r in cur.fetchall()]
    status = AccountStatus.RESTRICTED.value if types else AccountStatus.ACTIVE.value
    conn.execute(
        """
        UPDATE account SET restriction_reasons_json = ?, account_status = ?
        WHERE account_id = ?
        """,
        (json.dumps(types), status, account_id),
    )


def apply_account_restriction(
    conn: sqlite3.Connection,
    *,
    account_id: str,
    restriction_type: RestrictionType,
    reason: str,
    applied_at: datetime,
) -> Restriction:
    _ = reason
    rid = _new_id("R")
    conn.execute(
        """
        INSERT INTO restriction (
            restriction_id, account_id, restriction_type, applied_date,
            lift_eligible_after, requires_human_to_lift
        ) VALUES (?, ?, ?, ?, NULL, 0)
        """,
        (
            rid,
            account_id,
            restriction_type.value if isinstance(restriction_type, RestrictionType) else restriction_type,
            applied_at.isoformat(),
        ),
    )
    _sync_account_restrictions(conn, account_id)
    conn.commit()
    out = conn.execute("SELECT * FROM restriction WHERE restriction_id = ?", (rid,)).fetchone()
    assert out is not None
    return _row_restriction(out)


def lift_account_restriction(
    conn: sqlite3.Connection,
    *,
    restriction_id: str,
    reason: str,
    at: datetime,
) -> Restriction:
    _ = reason, at
    cur = conn.execute(
        "SELECT account_id FROM restriction WHERE restriction_id = ?",
        (restriction_id,),
    )
    row = cur.fetchone()
    if row is None:
        msg = f"restriction not found: {restriction_id}"
        raise ValueError(msg)
    account_id = row["account_id"]
    out = conn.execute("SELECT * FROM restriction WHERE restriction_id = ?", (restriction_id,)).fetchone()
    assert out is not None
    model = _row_restriction(out)
    conn.execute("DELETE FROM restriction WHERE restriction_id = ?", (restriction_id,))
    _sync_account_restrictions(conn, account_id)
    conn.commit()
    return model


def report_fraud(
    conn: sqlite3.Connection,
    *,
    customer_id: str,
    transaction_ids: list[str],
    fraud_type: FraudType,
    reported_at: datetime,
) -> FraudReport:
    fid = _new_id("FR")
    conn.execute(
        """
        INSERT INTO fraud_report (
            fraud_report_id, customer_id, transaction_ids_json, fraud_type,
            report_status, reported_date
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            fid,
            customer_id,
            json.dumps(transaction_ids),
            fraud_type.value if isinstance(fraud_type, FraudType) else fraud_type,
            FraudReportStatus.REPORTED.value,
            reported_at.isoformat(),
        ),
    )
    conn.commit()
    out = conn.execute("SELECT * FROM fraud_report WHERE fraud_report_id = ?", (fid,)).fetchone()
    assert out is not None
    return _row_fraud_report(out)


def escalate_to_human(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
    reason: str,
    urgency: str,
    at: datetime,
) -> Interaction:
    _ = reason, urgency, at
    conn.execute(
        "UPDATE interaction SET escalated_to_human = 1 WHERE interaction_id = ?",
        (interaction_id,),
    )
    conn.commit()
    out = conn.execute("SELECT * FROM interaction WHERE interaction_id = ?", (interaction_id,)).fetchone()
    if out is None:
        msg = f"interaction not found: {interaction_id}"
        raise ValueError(msg)
    return _row_interaction(out)


def request_documentation(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
    customer_id: str,
    document_type: str,
    deadline: str,
    created_at: datetime,
) -> None:
    dr_id = _new_id("DR")
    conn.execute(
        """
        INSERT INTO documentation_request (
            documentation_request_id, interaction_id, customer_id,
            document_type, deadline, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (dr_id, interaction_id, customer_id, document_type, deadline, created_at.isoformat()),
    )
    conn.commit()


def send_customer_message(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
    customer_id: str,
    message_text: str,
    message_category: str,
    created_at: datetime,
) -> None:
    mid = _new_id("MS")
    conn.execute(
        """
        INSERT INTO outbound_message (
            outbound_message_id, interaction_id, customer_id,
            message_text, message_category, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (mid, interaction_id, customer_id, message_text, message_category, created_at.isoformat()),
    )
    conn.commit()


def log_consumer_duty_assessment(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
    customer_id: str,
    vulnerability_indicators: list[str],
    fair_value_check_passed: bool,
    clear_communication_check_passed: bool,
    assessment_at: datetime,
) -> ConsumerDutyAssessment:
    aid = _new_id("CDA")
    conn.execute(
        """
        INSERT INTO consumer_duty_assessment (
            assessment_id, customer_id, interaction_id,
            vulnerability_indicators_json, fair_value_check_passed,
            clear_communication_check_passed, assessment_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            aid,
            customer_id,
            interaction_id,
            json.dumps(vulnerability_indicators),
            int(fair_value_check_passed),
            int(clear_communication_check_passed),
            assessment_at.isoformat(),
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM consumer_duty_assessment WHERE assessment_id = ?",
        (aid,),
    ).fetchone()
    assert row is not None
    return ConsumerDutyAssessment.model_validate(
        {
            "assessment_id": row["assessment_id"],
            "customer_id": row["customer_id"],
            "interaction_id": row["interaction_id"],
            "vulnerability_indicators": json.loads(row["vulnerability_indicators_json"]),
            "fair_value_check_passed": bool(row["fair_value_check_passed"]),
            "clear_communication_check_passed": bool(row["clear_communication_check_passed"]),
            "assessment_date": row["assessment_date"],
        },
    )
