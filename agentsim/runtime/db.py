from __future__ import annotations

import json
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

from agentsim.runtime.models import (
    Account,
    Card,
    ConsumerDutyAssessment,
    Customer,
    Dispute,
    FraudReport,
    Interaction,
    Refund,
    Restriction,
    Transaction,
)
from agentsim.runtime.schema import SCHEMA_SQL


def open_memory_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def load_seed_dict(conn: sqlite3.Connection, seed: dict[str, Any]) -> None:
    for c in seed.get("customers", []):
        cust = Customer.model_validate(c)
        conn.execute(
            """
            INSERT INTO customer (
                customer_id, kyc_status, account_tier, vulnerable_flag, pep_flag,
                sanctions_flag, joint_account, account_open_date,
                dispute_count_last_12m, prior_goodwill_credits_last_12m_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cust.customer_id,
                cust.kyc_status,
                cust.account_tier,
                int(cust.vulnerable_flag),
                int(cust.pep_flag),
                int(cust.sanctions_flag),
                int(cust.joint_account),
                cust.account_open_date.isoformat(),
                cust.dispute_count_last_12m,
                str(cust.prior_goodwill_credits_last_12m_amount),
            ),
        )

    for a in seed.get("accounts", []):
        acc = Account.model_validate(a)
        conn.execute(
            """
            INSERT INTO account (
                account_id, customer_id, balance_pence, available_balance_pence,
                currency, account_status, restriction_reasons_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                acc.account_id,
                acc.customer_id,
                acc.balance_pence,
                acc.available_balance_pence,
                acc.currency,
                acc.account_status,
                json.dumps([r for r in acc.restriction_reasons]),
            ),
        )

    for card in seed.get("cards", []):
        c = Card.model_validate(card)
        conn.execute(
            """
            INSERT INTO card (card_id, account_id, card_status, card_type)
            VALUES (?, ?, ?, ?)
            """,
            (c.card_id, c.account_id, c.card_status, c.card_type),
        )

    for t in seed.get("transactions", []):
        tx = Transaction.model_validate(t)
        conn.execute(
            """
            INSERT INTO transaction_row (
                transaction_id, account_id, card_id, merchant_name, merchant_category,
                amount_pence, currency, transaction_date, posted_date, status,
                is_section75_eligible, chargeback_window_days
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx.transaction_id,
                tx.account_id,
                tx.card_id,
                tx.merchant_name,
                tx.merchant_category,
                tx.amount_pence,
                tx.currency,
                tx.transaction_date.isoformat(),
                tx.posted_date.isoformat(),
                tx.status,
                int(tx.is_section75_eligible),
                tx.chargeback_window_days,
            ),
        )

    for d in seed.get("disputes", []):
        disp = Dispute.model_validate(d)
        conn.execute(
            """
            INSERT INTO dispute (
                dispute_id, transaction_id, customer_id, dispute_type, dispute_status,
                opened_date, evidence_documents_json, outcome_amount_pence,
                customer_statement
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                disp.dispute_id,
                disp.transaction_id,
                disp.customer_id,
                disp.dispute_type,
                disp.dispute_status,
                disp.opened_date.isoformat(),
                json.dumps(disp.evidence_documents),
                disp.outcome_amount_pence,
                disp.customer_statement,
            ),
        )

    for r in seed.get("refunds", []):
        ref = Refund.model_validate(r)
        conn.execute(
            """
            INSERT INTO refund (
                refund_id, transaction_id, customer_id, refund_type, amount_pence,
                requires_approval, approval_status, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ref.refund_id,
                ref.transaction_id,
                ref.customer_id,
                ref.refund_type,
                ref.amount_pence,
                int(ref.requires_approval),
                ref.approval_status,
                ref.created_date.isoformat(),
            ),
        )

    for r in seed.get("restrictions", []):
        rest = Restriction.model_validate(r)
        conn.execute(
            """
            INSERT INTO restriction (
                restriction_id, account_id, restriction_type, applied_date,
                lift_eligible_after, requires_human_to_lift
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rest.restriction_id,
                rest.account_id,
                rest.restriction_type,
                rest.applied_date.isoformat(),
                rest.lift_eligible_after.isoformat() if rest.lift_eligible_after else None,
                int(rest.requires_human_to_lift),
            ),
        )

    for f in seed.get("fraud_reports", []):
        fr = FraudReport.model_validate(f)
        conn.execute(
            """
            INSERT INTO fraud_report (
                fraud_report_id, customer_id, transaction_ids_json, fraud_type,
                report_status, reported_date
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                fr.fraud_report_id,
                fr.customer_id,
                json.dumps(fr.transaction_ids),
                fr.fraud_type,
                fr.report_status,
                fr.reported_date.isoformat(),
            ),
        )

    for i in seed.get("interactions", []):
        inter = Interaction.model_validate(i)
        actions = [tc.model_dump(mode="json") for tc in inter.actions_taken]
        conn.execute(
            """
            INSERT INTO interaction (
                interaction_id, customer_id, channel, started_at,
                actions_taken_json, escalated_to_human
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inter.interaction_id,
                inter.customer_id,
                inter.channel,
                inter.started_at.isoformat(),
                json.dumps(actions),
                int(inter.escalated_to_human),
            ),
        )

    for a in seed.get("consumer_duty_assessments", []):
        cda = ConsumerDutyAssessment.model_validate(a)
        conn.execute(
            """
            INSERT INTO consumer_duty_assessment (
                assessment_id, customer_id, interaction_id,
                vulnerability_indicators_json, fair_value_check_passed,
                clear_communication_check_passed, assessment_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cda.assessment_id,
                cda.customer_id,
                cda.interaction_id,
                json.dumps(cda.vulnerability_indicators),
                int(cda.fair_value_check_passed),
                int(cda.clear_communication_check_passed),
                cda.assessment_date.isoformat(),
            ),
        )

    conn.commit()


def load_seed_path(conn: sqlite3.Connection, path: str | Path) -> None:
    raw = Path(path).read_text(encoding="utf-8")
    load_seed_dict(conn, json.loads(raw))


def load_builtin_seed(conn: sqlite3.Connection) -> None:
    """Load the bundled minimal fixture (Slice A)."""
    pkg = "agentsim.runtime.data"
    with resources.files(pkg).joinpath("seed_minimal.json").open("r", encoding="utf-8") as f:
        load_seed_dict(conn, json.load(f))
