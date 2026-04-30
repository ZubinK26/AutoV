from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KycStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    FAILED = "FAILED"


class AccountTier(str, Enum):
    STANDARD = "STANDARD"
    PLUS = "PLUS"
    PREMIUM = "PREMIUM"
    BUSINESS = "BUSINESS"


class Currency(str, Enum):
    GBP = "GBP"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"
    RESTRICTED = "RESTRICTED"


class RestrictionType(str, Enum):
    AML_REVIEW = "AML_REVIEW"
    FRAUD_HOLD = "FRAUD_HOLD"
    SANCTIONS_BLOCK = "SANCTIONS_BLOCK"
    COURT_ORDER = "COURT_ORDER"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    CUSTOMER_REQUESTED = "CUSTOMER_REQUESTED"


class CardStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class CardType(str, Enum):
    DEBIT = "DEBIT"
    VIRTUAL = "VIRTUAL"


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    POSTED = "POSTED"
    REVERSED = "REVERSED"
    DISPUTED = "DISPUTED"


class DisputeType(str, Enum):
    UNAUTHORIZED = "UNAUTHORIZED"
    MERCHANT_REFUSED = "MERCHANT_REFUSED"
    GOODS_NOT_RECEIVED = "GOODS_NOT_RECEIVED"
    GOODS_NOT_AS_DESCRIBED = "GOODS_NOT_AS_DESCRIBED"
    SECTION_75 = "SECTION_75"
    DUPLICATE_CHARGE = "DUPLICATE_CHARGE"


class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"
    WITHDRAWN = "WITHDRAWN"


class RefundType(str, Enum):
    MERCHANT_REFUND = "MERCHANT_REFUND"
    DISPUTE_REFUND = "DISPUTE_REFUND"
    SECTION_75_REFUND = "SECTION_75_REFUND"
    GOODWILL_CREDIT = "GOODWILL_CREDIT"
    FEE_REVERSAL = "FEE_REVERSAL"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AUTO_APPROVED = "AUTO_APPROVED"


class FraudType(str, Enum):
    APP_FRAUD = "APP_FRAUD"
    CARD_FRAUD = "CARD_FRAUD"
    IDENTITY_THEFT = "IDENTITY_THEFT"
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    SCAM = "SCAM"


class FraudReportStatus(str, Enum):
    REPORTED = "REPORTED"
    INVESTIGATING = "INVESTIGATING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class Channel(str, Enum):
    CHAT = "CHAT"
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"


class AuditDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    NA = "NA"


class Customer(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    customer_id: str
    kyc_status: KycStatus
    account_tier: AccountTier
    vulnerable_flag: bool
    pep_flag: bool
    sanctions_flag: bool
    joint_account: bool
    account_open_date: date
    dispute_count_last_12m: int = 0
    prior_goodwill_credits_last_12m_amount: Decimal = Field(
        default=Decimal("0"),
        description="Major currency units as decimal (seed uses string).",
    )


class Account(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    account_id: str
    customer_id: str
    balance_pence: int
    available_balance_pence: int
    currency: Currency = Currency.GBP
    account_status: AccountStatus
    restriction_reasons: list[RestrictionType] = Field(default_factory=list)


class Card(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    card_id: str
    account_id: str
    card_status: CardStatus
    card_type: CardType


class Transaction(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    transaction_id: str
    account_id: str
    card_id: str | None
    merchant_name: str
    merchant_category: str
    amount_pence: int
    currency: Currency = Currency.GBP
    transaction_date: datetime
    posted_date: datetime
    status: TransactionStatus
    is_section75_eligible: bool
    chargeback_window_days: int


class Dispute(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    dispute_id: str
    transaction_id: str
    customer_id: str
    dispute_type: DisputeType
    dispute_status: DisputeStatus
    opened_date: datetime
    evidence_documents: list[str] = Field(default_factory=list)
    outcome_amount_pence: int | None = None
    customer_statement: str = ""


class Decision(BaseModel):
    """Runtime policy verdict for a proposed ToolCall (agentsim/02–03)."""

    allow: bool
    unsat_core: list[str] | None = None
    explanation: str = ""


class ToolBlockedResult(BaseModel):
    """Returned to the agent when a write is blocked (instead of a success payload)."""

    model_config = ConfigDict(use_enum_values=True)

    blocked: bool = True
    reasons: str
    unsat_core: list[str] | None = None


class Refund(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    refund_id: str
    transaction_id: str | None
    customer_id: str
    refund_type: RefundType
    amount_pence: int
    requires_approval: bool
    approval_status: ApprovalStatus
    created_date: datetime


class Restriction(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    restriction_id: str
    account_id: str
    restriction_type: RestrictionType
    applied_date: datetime
    lift_eligible_after: datetime | None
    requires_human_to_lift: bool


class FraudReport(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    fraud_report_id: str
    customer_id: str
    transaction_ids: list[str]
    fraud_type: FraudType
    report_status: FraudReportStatus
    reported_date: datetime


class ConsumerDutyAssessment(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    assessment_id: str
    customer_id: str
    interaction_id: str
    vulnerability_indicators: list[str]
    fair_value_check_passed: bool
    clear_communication_check_passed: bool
    assessment_date: datetime


class ToolCall(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    proposed_at: datetime
    interaction_id: str


class Interaction(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    interaction_id: str
    customer_id: str
    channel: Channel
    started_at: datetime
    actions_taken: list[ToolCall] = Field(default_factory=list)
    escalated_to_human: bool = False


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    interaction_id: str
    timestamp: datetime
    tool_name: str
    parameters: dict[str, Any]
    decision: AuditDecision
    unsat_core: list[str] | None = None
    explanation: str | None = None
    policy_version: str
    rules_consulted: list[str] = Field(default_factory=list)

