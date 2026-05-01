from __future__ import annotations

import uuid
from typing import Any, TYPE_CHECKING

from agentsim_simplified.entities import Refund, RefundError, SchemaError, StateBundle, ToolCall
from agentsim_simplified.seed_data import DBShape
from agentsim_simplified.validator import validate_apply_refund

if TYPE_CHECKING:
    from agentsim_simplified.simpl_checker import SimplPolicyChecker


def _require_keys(d: dict[str, Any], keys: set[str]) -> None:
    if set(d.keys()) != keys:
        msg = f"expected keys {sorted(keys)}, got {sorted(d.keys())}"
        raise SchemaError(msg)


def lookup_bundle(db: DBShape, transaction_id: str) -> StateBundle | None:
    txns: dict = db["transactions"]
    accs: dict = db["accounts"]
    custs: dict = db["customers"]
    t = txns.get(transaction_id)
    if t is None:
        return None
    a = accs.get(t.account_id)
    if a is None:
        return None
    c = custs.get(a.customer_id)
    if c is None:
        return None
    return StateBundle(customer=c, account=a, transaction=t)


def apply_refund(
    db: DBShape,
    call: ToolCall,
    *,
    checker: SimplPolicyChecker | None = None,
) -> Refund | RefundError:
    _require_keys(
        call.parameters,
        {"transaction_id", "amount_pence", "refund_type", "reason"},
    )
    txid = str(call.parameters["transaction_id"])
    bundle = lookup_bundle(db, txid)
    decision = validate_apply_refund(bundle, call, checker=checker)
    if not decision.allow:
        return RefundError(decision.explanation, tuple(decision.unsat_core))
    refund_id = f"RF-{uuid.uuid4().hex[:8].upper()}"
    c = bundle.customer  # type: ignore[union-attr]
    t = bundle.transaction  # type: ignore[union-attr]
    rf = Refund(
        refund_id=refund_id,
        transaction_id=t.transaction_id,
        customer_id=c.customer_id,
        amount_pence=int(call.parameters["amount_pence"]),
        refund_type=call.parameters["refund_type"],  # type: ignore[arg-type]
        reason=str(call.parameters["reason"]),
    )
    db["refunds"][refund_id] = rf
    return rf
