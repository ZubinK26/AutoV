"""Ground scenarios for ``policy_model_refined.smt2`` (ToolCall + world slice → SMT-LIB fragment)."""

from __future__ import annotations

from dataclasses import dataclass, field


# One-hot ToolCall discriminators (must match policy_model_refined.smt2).
_TOOLCALL_KIND_FUNCS: tuple[str, ...] = (
    "is-apply-refund-call",
    "is-initiate-dispute-call",
    "is-cancel-dispute-call",
    "is-freeze-card-call",
    "is-unfreeze-card-call",
    "is-apply-restriction-call",
    "is-lift-restriction-call",
    "is-report-fraud-call",
    "is-send-message-call",
    "is-escalate-call",
    "is-log-assessment-call",
    "is-request-doc-call",
)

# Map scenario primary_tool (Python / agentsim write surface) → active discriminator.
_PRIMARY_TOOL: dict[str, str] = {
    "apply_refund": "is-apply-refund-call",
    "apply_goodwill_credit": "is-apply-refund-call",
    "apply_fee_reversal": "is-apply-refund-call",
    "initiate_dispute": "is-initiate-dispute-call",
    "cancel_dispute": "is-cancel-dispute-call",
    "freeze_card": "is-freeze-card-call",
    "unfreeze_card": "is-unfreeze-card-call",
    "apply_account_restriction": "is-apply-restriction-call",
    "lift_account_restriction": "is-lift-restriction-call",
    "report_fraud": "is-report-fraud-call",
    "send_customer_message": "is-send-message-call",
    "request_documentation": "is-request-doc-call",
    "log_consumer_duty_assessment": "is-log-assessment-call",
    "escalate": "is-escalate-call",
    "escalate_to_human": "is-escalate-call",
}

# Every write tool from agentsim/01_simulation_environment.md (aligned with write_tools.py).
SPEC_WRITE_TOOL_PRIMARIES: tuple[str, ...] = tuple(sorted(_PRIMARY_TOOL.keys()))


def _dispute_type(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {
        "UNAUTHORIZED": "unauthorized",
        "MERCHANT_REFUSED": "merchant-refused",
        "GOODS_NOT_RECEIVED": "goods-not-received",
        "GOODS_NOT_AS_DESCRIBED": "goods-not-as-described",
        "SECTION_75": "section-75",
        "DUPLICATE_CHARGE": "duplicate-charge",
    }
    if s not in m:
        msg = f"unknown dispute type {sym!r}"
        raise ValueError(msg)
    return m[s]


def _dispute_status_cancel(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {"OPEN": "dispute-open", "UNDER_REVIEW": "dispute-under-review"}
    if s not in m:
        msg = f"unknown cancelable dispute status {sym!r}"
        raise ValueError(msg)
    return m[s]


def _kyc(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {"VERIFIED": "verified", "PENDING": "pending", "FAILED": "failed"}
    if s not in m:
        msg = f"unknown KYC {sym!r}"
        raise ValueError(msg)
    return m[s]


def _acct(sym: str) -> str:
    s = sym.upper()
    m = {
        "ACTIVE": "active",
        "FROZEN": "frozen",
        "CLOSED": "closed",
        "RESTRICTED": "restricted",
    }
    if s not in m:
        msg = f"unknown account status {sym!r}"
        raise ValueError(msg)
    return m[s]


def _txn_status(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {
        "PENDING": "txn-pending",
        "POSTED": "txn-posted",
        "REVERSED": "txn-reversed",
        "DISPUTED": "txn-disputed",
    }
    if s not in m:
        msg = f"unknown transaction status {sym!r}"
        raise ValueError(msg)
    return m[s]


def _refund_type(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {
        "MERCHANT_REFUND": "merchant-refund",
        "DISPUTE_REFUND": "dispute-refund",
        "SECTION_75_REFUND": "section-75-refund",
        "GOODWILL_CREDIT": "goodwill-credit",
        "FEE_REVERSAL": "fee-reversal",
    }
    if s not in m:
        msg = f"unknown refund type {sym!r}"
        raise ValueError(msg)
    return m[s]


def _restriction_type(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {
        "AML_REVIEW": "aml-review",
        "FRAUD_HOLD": "fraud-hold",
        "SANCTIONS_BLOCK": "sanctions-block",
        "COURT_ORDER": "court-order",
        "COMPLIANCE_REVIEW": "compliance-review",
        "CUSTOMER_REQUESTED": "customer-requested",
    }
    if s not in m:
        msg = f"unknown restriction type {sym!r}"
        raise ValueError(msg)
    return m[s]


def _fraud_type(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {"APP_FRAUD": "app-fraud", "CARD_FRAUD": "card-fraud"}
    if s not in m:
        msg = f"unknown fraud report type {sym!r}"
        raise ValueError(msg)
    return m[s]


def _message_category(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {"PROMOTIONAL": "promotional", "COLLECTIONS": "collections"}
    if s not in m:
        msg = f"unknown message category {sym!r}"
        raise ValueError(msg)
    return m[s]


def _doc_type(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {"PROOF_OF_ADDRESS": "proof-of-address", "OTHER_DOC": "other-doc"}
    if s not in m:
        msg = f"unknown documentation type {sym!r}"
        raise ValueError(msg)
    return m[s]


@dataclass
class GuardrailsScenario:
    """
    Minimal snapshot for one ``ToolCall`` (``sim_tc``) plus **sim_c** / **sim_a** / **sim_t**.

    Emit SMT2 that sets discriminators, DB flags, and entity fields used by guardrails rules.
    """

    primary_tool: str
    customer_kyc: str = "VERIFIED"
    customer_vulnerable: bool = False
    customer_sanctions: bool = False
    customer_exists_in_db: bool = True
    account_status: str = "ACTIVE"
    account_exists_in_db: bool = True
    interaction_escalated: bool = False
    interaction_exists_in_db: bool = True
    human_approval_granted: bool = False
    duplicate_prior_allowed: bool = False
    references_missing_entity: bool = False
    has_out_of_bounds_numeric: bool = False
    refund_type: str = "GOODWILL_CREDIT"
    refund_amount_pence: int = 5_000
    transaction_exists_in_db: bool = True
    transaction_status: str = "POSTED"
    transaction_amount_pence: int = 10_000
    transaction_is_debit: bool = True
    transaction_is_fee: bool = False
    days_since_posted: int = 30
    recent_goodwill_credit_total: int = 0
    recent_dispute_count: int = 0
    dispute_type: str = "UNAUTHORIZED"
    cancel_dispute_status: str = "OPEN"
    apply_restriction_type: str = "CUSTOMER_REQUESTED"
    lift_restriction_type: str = "COMPLIANCE_REVIEW"
    restriction_human_action_required: bool = False
    fraud_report_type: str = "APP_FRAUD"
    message_category: str = "PROMOTIONAL"
    documentation_type: str = "OTHER_DOC"
    documentation_deadline_days: int = 5
    extra_asserts: list[str] = field(default_factory=list)

    def to_smt2_fragment(self, *, instance_suffix: str = "") -> str:
        pt_raw = self.primary_tool
        if pt_raw not in _PRIMARY_TOOL:
            msg = f"primary_tool must be one of {sorted(_PRIMARY_TOOL)}"
            raise ValueError(msg)
        active = _PRIMARY_TOOL[pt_raw]

        refund_type_eff = self.refund_type
        if pt_raw == "apply_goodwill_credit":
            refund_type_eff = "GOODWILL_CREDIT"
        elif pt_raw == "apply_fee_reversal":
            refund_type_eff = "FEE_REVERSAL"

        if pt_raw in ("apply_goodwill_credit", "apply_fee_reversal"):
            pt = "apply_refund"
        elif pt_raw == "escalate_to_human":
            pt = "escalate"
        else:
            pt = pt_raw

        if self.transaction_is_debit:
            tamt = abs(self.transaction_amount_pence)
        else:
            tamt = -abs(self.transaction_amount_pence)
        tc = f"sim_tc{instance_suffix}"
        c = f"sim_c{instance_suffix}"
        a = f"sim_a{instance_suffix}"
        t = f"sim_t{instance_suffix}"
        card = f"sim_card{instance_suffix}"
        d_const = f"sim_d{instance_suffix}"
        r_const = f"sim_r{instance_suffix}"
        lines: list[str] = [
            "; --- guardrails scenario fragment (generated) ---",
            f"(declare-const {tc} ToolCall)",
            f"(declare-const {c} Customer)",
            f"(declare-const {a} Account)",
            f"(declare-const {t} Transaction)",
        ]

        for fn in _TOOLCALL_KIND_FUNCS:
            val = "true" if fn == active else "false"
            lines.append(f"(assert (= ({fn} {tc}) {val}))")

        lines.extend(
            [
                f"(assert (= (is-write-tool-call {tc}) true))",
                f"(assert (= (has-typed-parameters {tc}) true))",
                f"(assert (= (customer-exists-in-db {c}) {str(self.customer_exists_in_db).lower()}))",
                f"(assert (= (account-exists-in-db {a}) {str(self.account_exists_in_db).lower()}))",
                f"(assert (= (transaction-exists-in-db {t}) {str(self.transaction_exists_in_db).lower()}))",
                f"(assert (= (is-vulnerable {c}) {str(self.customer_vulnerable).lower()}))",
                f"(assert (= (has-sanctions {c}) {str(self.customer_sanctions).lower()}))",
                f"(assert (= (kyc-status {c}) {_kyc(self.customer_kyc)}))",
                f"(assert (= (account-status {a}) {_acct(self.account_status)}))",
                f"(assert (= (account-owner {a}) {c}))",
                f"(assert (= (transaction-account {t}) {a}))",
                f"(assert (= (human-approval-granted {tc}) {str(self.human_approval_granted).lower()}))",
                f"(assert (= (is-duplicate-of-prior-allowed-call-in-interaction {tc}) {str(self.duplicate_prior_allowed).lower()}))",
                f"(assert (= (references-missing-entity {tc}) {str(self.references_missing_entity).lower()}))",
                f"(assert (= (has-out-of-bounds-numeric-parameter {tc}) {str(self.has_out_of_bounds_numeric).lower()}))",
                f"(assert (= (has-been-escalated current-interaction) {str(self.interaction_escalated).lower()}))",
                f"(assert (= (interaction-exists-in-db current-interaction) {str(self.interaction_exists_in_db).lower()}))",
                f"(assert (= (recent-goodwill-credit-total {c}) {self.recent_goodwill_credit_total}))",
                f"(assert (= (recent-dispute-count {c}) {self.recent_dispute_count}))",
                f"(assert (= (transaction-status {t}) {_txn_status(self.transaction_status)}))",
                f"(assert (= (transaction-amount-pence {t}) {tamt}))",
                f"(assert (= (is-debit {t}) {str(self.transaction_is_debit).lower()}))",
                f"(assert (= (is-credit {t}) {str(not self.transaction_is_debit).lower()}))",
                f"(assert (= (is-fee {t}) {str(self.transaction_is_fee).lower()}))",
                f"(assert (= (days-since-posted {t}) {self.days_since_posted}))",
                f"(assert (= (has-duplicate-candidate-within-window {t}) false))",
                f"(assert (= (is-section-75-eligible {t}) true))",
                f"(assert (= (fee-already-reversed {t}) false))",
            ]
        )

        if pt == "apply_refund":
            rt = _refund_type(refund_type_eff)
            lines.extend(
                [
                    f"(assert (= (refund-call-type {tc}) {rt}))",
                    f"(assert (= (refund-call-amount-pence {tc}) {self.refund_amount_pence}))",
                    f"(assert (= (refund-call-customer {tc}) {c}))",
                    f"(assert (= (refund-call-account {tc}) {a}))",
                    f"(assert (= (refund-call-transaction {tc}) {t}))",
                ]
            )

        if pt == "escalate":
            lines.extend(
                [
                    f"(assert (= (escalate-call-customer {tc}) {c}))",
                ]
            )

        if pt in ("freeze_card", "unfreeze_card"):
            cst = "card-active" if pt == "freeze_card" else "card-frozen"
            lines.extend(
                [
                    f"(declare-const {card} Card)",
                    f"(assert (= (card-exists-in-db {card}) true))",
                    f"(assert (= (card-status {card}) {cst}))",
                    f"(assert (= (card-account {card}) {a}))",
                ]
            )
            if pt == "freeze_card":
                lines.append(f"(assert (= (freeze-card-call-card {tc}) {card}))")
            else:
                lines.append(f"(assert (= (unfreeze-card-call-card {tc}) {card}))")

        if pt == "initiate_dispute":
            lines.extend(
                [
                    f"(assert (= (dispute-call-transaction {tc}) {t}))",
                    f"(assert (= (dispute-call-customer {tc}) {c}))",
                    f"(assert (= (dispute-call-type {tc}) {_dispute_type(self.dispute_type)}))",
                    f"(assert (not (exists ((d Dispute)) (and (= (dispute-transaction d) {t}) (or (= (dispute-status d) dispute-open) (= (dispute-status d) dispute-under-review))))))",
                ]
            )

        if pt == "cancel_dispute":
            lines.extend(
                [
                    f"(declare-const {d_const} Dispute)",
                    f"(assert (= (dispute-exists-in-db {d_const}) true))",
                    f"(assert (= (dispute-transaction {d_const}) {t}))",
                    f"(assert (= (dispute-status {d_const}) {_dispute_status_cancel(self.cancel_dispute_status)}))",
                    f"(assert (= (cancel-dispute-call-dispute {tc}) {d_const}))",
                ]
            )

        if pt == "apply_account_restriction":
            lines.extend(
                [
                    f"(assert (= (apply-restriction-call-account {tc}) {a}))",
                    f"(assert (= (apply-restriction-call-type {tc}) {_restriction_type(self.apply_restriction_type)}))",
                ]
            )

        if pt == "lift_account_restriction":
            lines.extend(
                [
                    f"(declare-const {r_const} Restriction)",
                    f"(assert (= (restriction-exists-in-db {r_const}) true))",
                    f"(assert (= (is-active-restriction {r_const}) true))",
                    f"(assert (= (human-action-required {r_const}) {str(self.restriction_human_action_required).lower()}))",
                    f"(assert (= (restriction-account {r_const}) {a}))",
                    f"(assert (= (restriction-type {r_const}) {_restriction_type(self.lift_restriction_type)}))",
                    f"(assert (= (lift-restriction-call-restriction {tc}) {r_const}))",
                ]
            )

        if pt == "report_fraud":
            ft = _fraud_type(self.fraud_report_type)
            lines.extend(
                [
                    f"(assert (= (report-fraud-call-customer {tc}) {c}))",
                    f"(assert (= (report-fraud-call-type {tc}) {ft}))",
                    f"(assert (report-fraud-call-references-transaction {tc} {t}))",
                    f"(assert (= (is-account-takeover {tc}) false))",
                    f"(assert (= (is-identity-theft {tc}) false))",
                ]
            )
            if ft == "card-fraud":
                lines.append(f"(assert (= (has-card-identifier {t}) true))")

        if pt == "send_customer_message":
            lines.extend(
                [
                    f"(assert (= (message-call-recipient {tc}) {c}))",
                    f"(assert (= (message-call-category {tc}) {_message_category(self.message_category)}))",
                ]
            )

        if pt == "request_documentation":
            lines.extend(
                [
                    f"(assert (= (request-doc-call-customer {tc}) {c}))",
                    f"(assert (= (request-doc-call-deadline {tc}) {self.documentation_deadline_days}))",
                    f"(assert (= (request-doc-call-type {tc}) {_doc_type(self.documentation_type)}))",
                ]
            )

        if pt == "log_consumer_duty_assessment":
            lines.append(f"(assert (= (log-assessment-call-customer {tc}) {c}))")

        for raw in self.extra_asserts:
            subst = raw
            subst = subst.replace("sim_card", card)
            subst = subst.replace("sim_tc", tc)
            subst = subst.replace("sim_c", c)
            subst = subst.replace("sim_a", a)
            subst = subst.replace("sim_t", t)
            subst = subst.replace("sim_d", d_const)
            subst = subst.replace("sim_r", r_const)
            lines.append(subst)

        return "\n".join(lines) + "\n"
