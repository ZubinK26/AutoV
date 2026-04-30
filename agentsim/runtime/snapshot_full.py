from __future__ import annotations

import json
import sqlite3
from typing import Any

from agentsim.runtime.models import ToolCall

__all__ = ["full_snapshot_for_call", "full_snapshot_builder"]


def full_snapshot_builder(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
):
    def build(call: ToolCall) -> dict[str, Any]:
        return full_snapshot_for_call(conn, interaction_id, call)

    return build


def full_snapshot_for_call(
    conn: sqlite3.Connection,
    interaction_id: str,
    call: ToolCall,
) -> dict[str, Any]:
    """State snapshot slice per write tool (agentsim/03 manifests, Python form)."""

    name = call.tool_name
    if name == "apply_goodwill_credit":
        return _snap_goodwill(conn, call, interaction_id)
    if name == "initiate_dispute":
        return _snap_initiate_dispute(conn, call, interaction_id)
    if name == "cancel_dispute":
        return _snap_cancel_dispute(conn, call, interaction_id)
    if name == "apply_refund":
        return _snap_apply_refund(conn, call, interaction_id)
    if name == "apply_fee_reversal":
        return _snap_apply_fee_reversal(conn, call, interaction_id)
    if name in ("freeze_card", "unfreeze_card"):
        return _snap_card_action(conn, call, interaction_id)
    if name == "apply_account_restriction":
        return _snap_apply_account_restriction(conn, call, interaction_id)
    if name == "lift_account_restriction":
        return _snap_lift_account_restriction(conn, call, interaction_id)
    if name == "report_fraud":
        return _snap_report_fraud(conn, call, interaction_id)
    if name == "escalate_to_human":
        return _snap_escalate(conn, call, interaction_id)
    if name == "request_documentation":
        return _snap_customer_only(conn, call, interaction_id)
    if name == "send_customer_message":
        return _snap_customer_only(conn, call, interaction_id)
    if name == "log_consumer_duty_assessment":
        return _snap_consumer_duty(conn, call, interaction_id)
    return {}


def _row_customer(conn: sqlite3.Connection, customer_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM customer WHERE customer_id = ?", (customer_id,)).fetchone()
    if row is None:
        return None
    return {
        "customer_id": row["customer_id"],
        "kyc_status": row["kyc_status"],
        "account_tier": row["account_tier"],
        "vulnerable_flag": bool(row["vulnerable_flag"]),
        "pep_flag": bool(row["pep_flag"]),
        "sanctions_flag": bool(row["sanctions_flag"]),
        "joint_account": bool(row["joint_account"]),
        "account_open_date": row["account_open_date"],
        "dispute_count_last_12m": row["dispute_count_last_12m"],
        "prior_goodwill_credits_last_12m_amount": str(row["prior_goodwill_credits_last_12m_amount"]),
    }


def _row_account(conn: sqlite3.Connection, account_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM account WHERE account_id = ?", (account_id,)).fetchone()
    if row is None:
        return None
    return {
        "account_id": row["account_id"],
        "customer_id": row["customer_id"],
        "balance_pence": row["balance_pence"],
        "available_balance_pence": row["available_balance_pence"],
        "currency": row["currency"],
        "account_status": row["account_status"],
        "restriction_reasons": json.loads(row["restriction_reasons_json"]),
    }


def _row_transaction(conn: sqlite3.Connection, transaction_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM transaction_row WHERE transaction_id = ?",
        (transaction_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "transaction_id": row["transaction_id"],
        "account_id": row["account_id"],
        "card_id": row["card_id"],
        "merchant_name": row["merchant_name"],
        "merchant_category": row["merchant_category"],
        "amount_pence": row["amount_pence"],
        "status": row["status"],
    }


def _row_card(conn: sqlite3.Connection, card_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM card WHERE card_id = ?", (card_id,)).fetchone()
    if row is None:
        return None
    return {
        "card_id": row["card_id"],
        "account_id": row["account_id"],
        "card_status": row["card_status"],
        "card_type": row["card_type"],
    }


def _open_disputes(conn: sqlite3.Connection, customer_id: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT dispute_id, transaction_id, dispute_type, dispute_status, opened_date
        FROM dispute WHERE customer_id = ? AND dispute_status IN ('OPEN', 'UNDER_REVIEW')
        """,
        (customer_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def _restrictions_for_account(conn: sqlite3.Connection, account_id: str) -> list[dict[str, Any]]:
    cur = conn.execute(
        "SELECT restriction_id, restriction_type, applied_date FROM restriction WHERE account_id = ?",
        (account_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def _goodwill_pence_12m(conn: sqlite3.Connection, customer_id: str) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(amount_pence), 0) AS s FROM refund
        WHERE customer_id = ? AND refund_type = 'GOODWILL_CREDIT'
        """,
        (customer_id,),
    ).fetchone()
    return int(row["s"] if row else 0)


def _latest_duty(conn: sqlite3.Connection, interaction_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT * FROM consumer_duty_assessment WHERE interaction_id = ?
        ORDER BY assessment_date DESC LIMIT 1
        """,
        (interaction_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "assessment_id": row["assessment_id"],
        "vulnerability_indicators": json.loads(row["vulnerability_indicators_json"]),
        "fair_value_check_passed": bool(row["fair_value_check_passed"]),
        "clear_communication_check_passed": bool(row["clear_communication_check_passed"]),
    }


def _snap_goodwill(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    cid = str(call.parameters.get("customer_id", ""))
    c = _row_customer(conn, cid)
    base: dict[str, Any] = {
        "interaction_id": interaction_id,
        "customer_id": cid,
        "customer_found": c is not None,
        "customer_vulnerable_flag": c["vulnerable_flag"] if c else False,
        "prior_goodwill_credits_last_12m_amount": (
            c["prior_goodwill_credits_last_12m_amount"] if c else "0"
        ),
    }
    base["goodwill_amount_pence_12m_rollup"] = _goodwill_pence_12m(conn, cid) if c else 0
    return base


def _snap_initiate_dispute(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    tid = str(call.parameters.get("transaction_id", ""))
    tx = _row_transaction(conn, tid)
    out: dict[str, Any] = {"interaction_id": interaction_id, "transaction_id": tid, "transaction": tx}
    if not tx:
        return out
    acc = _row_account(conn, tx["account_id"])
    out["account"] = acc
    if acc:
        cust = _row_customer(conn, acc["customer_id"])
        out["customer"] = cust
        out["customer_vulnerable_flag"] = cust["vulnerable_flag"] if cust else False
        out["open_disputes"] = _open_disputes(conn, acc["customer_id"])
        out["restrictions"] = _restrictions_for_account(conn, acc["account_id"])
        out["goodwill_amount_pence_12m_rollup"] = _goodwill_pence_12m(conn, acc["customer_id"])
    out["consumer_duty"] = _latest_duty(conn, interaction_id)
    return out


def _snap_cancel_dispute(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    did = str(call.parameters.get("dispute_id", ""))
    row = conn.execute("SELECT * FROM dispute WHERE dispute_id = ?", (did,)).fetchone()
    out: dict[str, Any] = {"interaction_id": interaction_id, "dispute_id": did, "dispute": None}
    if not row:
        return out
    out["dispute"] = dict(row)
    cust = _row_customer(conn, row["customer_id"])
    out["customer"] = cust
    tx = _row_transaction(conn, row["transaction_id"])
    out["transaction"] = tx
    if tx:
        out["restrictions"] = _restrictions_for_account(conn, tx["account_id"])
    out["consumer_duty"] = _latest_duty(conn, interaction_id)
    return out


def _snap_apply_refund(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    tid = str(call.parameters.get("transaction_id", ""))
    tx = _row_transaction(conn, tid)
    out: dict[str, Any] = {
        "interaction_id": interaction_id,
        "transaction_id": tid,
        "proposed_amount_pence": int(call.parameters.get("amount_pence", 0)),
        "refund_type": str(call.parameters.get("refund_type", "")),
        "transaction": tx,
    }
    if not tx:
        return out
    acc = _row_account(conn, tx["account_id"])
    out["account"] = acc
    if acc:
        cid = acc["customer_id"]
        out["customer"] = _row_customer(conn, cid)
        out["customer_vulnerable_flag"] = out["customer"]["vulnerable_flag"] if out["customer"] else False
        out["open_disputes"] = _open_disputes(conn, cid)
        out["restrictions"] = _restrictions_for_account(conn, tx["account_id"])
        out["goodwill_amount_pence_12m_rollup"] = _goodwill_pence_12m(conn, cid)
    out["consumer_duty"] = _latest_duty(conn, interaction_id)
    return out


def _snap_apply_fee_reversal(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    tid = str(call.parameters.get("transaction_id", ""))
    tx = _row_transaction(conn, tid)
    out: dict[str, Any] = {"interaction_id": interaction_id, "transaction": tx}
    if tx:
        acc = _row_account(conn, tx["account_id"])
        out["account"] = acc
        if acc:
            out["customer"] = _row_customer(conn, acc["customer_id"])
            out["restrictions"] = _restrictions_for_account(conn, tx["account_id"])
    return out


def _snap_card_action(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    card_id = str(call.parameters.get("card_id", ""))
    card = _row_card(conn, card_id)
    out: dict[str, Any] = {"interaction_id": interaction_id, "card": card}
    if card:
        acc = _row_account(conn, card["account_id"])
        out["account"] = acc
        if acc:
            out["customer"] = _row_customer(conn, acc["customer_id"])
            out["restrictions"] = _restrictions_for_account(conn, acc["account_id"])
    return out


def _snap_apply_account_restriction(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    aid = str(call.parameters.get("account_id", ""))
    acc = _row_account(conn, aid)
    out: dict[str, Any] = {
        "interaction_id": interaction_id,
        "account": acc,
        "restriction_type_requested": str(call.parameters.get("restriction_type", "")),
    }
    if acc:
        out["customer"] = _row_customer(conn, acc["customer_id"])
        out["restrictions"] = _restrictions_for_account(conn, aid)
    return out


def _snap_lift_account_restriction(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    rid = str(call.parameters.get("restriction_id", ""))
    row = conn.execute("SELECT * FROM restriction WHERE restriction_id = ?", (rid,)).fetchone()
    out: dict[str, Any] = {"interaction_id": interaction_id, "restriction_id": rid, "restriction": None}
    if not row:
        return out
    out["restriction"] = dict(row)
    out["account"] = _row_account(conn, row["account_id"])
    if out["account"]:
        out["customer"] = _row_customer(conn, out["account"]["customer_id"])
    return out


def _snap_report_fraud(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    cid = str(call.parameters.get("customer_id", ""))
    tx_ids = call.parameters.get("transaction_ids") or []
    out: dict[str, Any] = {
        "interaction_id": interaction_id,
        "customer": _row_customer(conn, cid),
        "transaction_ids": list(tx_ids),
        "transactions": [_row_transaction(conn, t) for t in tx_ids],
    }
    return out


def _snap_escalate(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM interaction WHERE interaction_id = ?", (interaction_id,)).fetchone()
    out: dict[str, Any] = {"interaction_id": interaction_id, "interaction": dict(row) if row else None}
    if row:
        out["customer"] = _row_customer(conn, row["customer_id"])
    return out


def _snap_customer_only(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    cid = str(call.parameters.get("customer_id", ""))
    c = _row_customer(conn, cid)
    return {
        "interaction_id": interaction_id,
        "customer_id": cid,
        "customer": c,
        "customer_vulnerable_flag": c["vulnerable_flag"] if c else False,
    }


def _snap_consumer_duty(conn: sqlite3.Connection, call: ToolCall, interaction_id: str) -> dict[str, Any]:
    cid = str(call.parameters.get("customer_id", ""))
    c = _row_customer(conn, cid)
    return {
        "interaction_id": interaction_id,
        "customer": c,
        "customer_vulnerable_flag": c["vulnerable_flag"] if c else False,
        "checks": call.parameters.get("checks") or {},
        "consumer_duty_prior": _latest_duty(conn, interaction_id),
    }