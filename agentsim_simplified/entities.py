from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Kyc = Literal["VERIFIED", "FAILED"]
AcctStatus = Literal["ACTIVE", "FROZEN", "CLOSED"]
TxnStatus = Literal["POSTED", "PENDING"]
RefundTypeLit = Literal["MERCHANT_REFUND", "GOODWILL_CREDIT"]


@dataclass(frozen=True)
class Customer:
    customer_id: str
    kyc_status: Kyc
    vulnerable_flag: bool
    recent_goodwill_credit_total_pence: int


@dataclass(frozen=True)
class Account:
    account_id: str
    customer_id: str
    status: AcctStatus
    has_sanctions_block: bool


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    account_id: str
    amount_pence: int
    status: TxnStatus


@dataclass(frozen=True)
class Refund:
    refund_id: str
    transaction_id: str
    customer_id: str
    amount_pence: int
    refund_type: RefundTypeLit
    reason: str


@dataclass(frozen=True)
class StateBundle:
    customer: Customer
    account: Account
    transaction: Transaction


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    parameters: dict[str, Any]


class SchemaError(ValueError):
    """Pre-validator schema violation."""


@dataclass(frozen=True)
class RefundError:
    reasons: str
    rule_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    allow: bool
    unsat_core: list[str]
    explanation: str
