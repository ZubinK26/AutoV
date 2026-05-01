"""Ground ``StateBundle`` + refund parameters to SMT-LIB for ``policy_model_refined_simpl.smt2``."""

from __future__ import annotations

from dataclasses import dataclass

from agentsim_simplified.entities import StateBundle


def _kyc(sym: str) -> str:
    m = {"VERIFIED": "verified", "FAILED": "failed"}
    s = sym.upper()
    if s not in m:
        msg = f"unknown KYC {sym!r}"
        raise ValueError(msg)
    return m[s]


def _txn_status(sym: str) -> str:
    m = {"POSTED": "posted", "PENDING": "pending"}
    s = sym.upper()
    if s not in m:
        msg = f"unknown transaction status {sym!r}"
        raise ValueError(msg)
    return m[s]


def _refund_type(sym: str) -> str:
    s = sym.upper().replace("-", "_")
    m = {"MERCHANT_REFUND": "merchant-refund", "GOODWILL_CREDIT": "goodwill-credit"}
    if s not in m:
        msg = f"unknown refund type {sym!r}"
        raise ValueError(msg)
    return m[s]


@dataclass
class RefundCallScenario:
    """
    One proposed refund + entity slice (``sim_r``, ``sim_c``, ``sim_a``, ``sim_t``).

    ``customer_exists_in_db`` / ``account_exists_in_db`` / ``transaction_exists_in_db`` implement
    refined-policy ``*-exists-in-db`` predicates for validation (missing lookup ⇒ false).
    """

    customer_exists_in_db: bool
    account_exists_in_db: bool
    transaction_exists_in_db: bool
    customer_kyc: str
    customer_vulnerable: bool
    customer_recent_goodwill_pence: int
    account_has_sanctions_block: bool
    transaction_amount_pence: int
    transaction_status: str
    refund_type: str
    refund_amount_pence: int

    @classmethod
    def from_bundle(
        cls,
        bundle: StateBundle | None,
        *,
        refund_type: str,
        refund_amount_pence: int,
    ) -> RefundCallScenario:
        if bundle is None:
            return cls(
                customer_exists_in_db=False,
                account_exists_in_db=False,
                transaction_exists_in_db=False,
                customer_kyc="VERIFIED",
                customer_vulnerable=False,
                customer_recent_goodwill_pence=0,
                account_has_sanctions_block=False,
                transaction_amount_pence=1,
                transaction_status="POSTED",
                refund_type=refund_type,
                refund_amount_pence=refund_amount_pence,
            )
        c, a, t = bundle.customer, bundle.account, bundle.transaction
        return cls(
            customer_exists_in_db=True,
            account_exists_in_db=True,
            transaction_exists_in_db=True,
            customer_kyc=c.kyc_status,
            customer_vulnerable=c.vulnerable_flag,
            customer_recent_goodwill_pence=c.recent_goodwill_credit_total_pence,
            account_has_sanctions_block=a.has_sanctions_block,
            transaction_amount_pence=t.amount_pence,
            transaction_status=t.status,
            refund_type=refund_type,
            refund_amount_pence=refund_amount_pence,
        )

    def to_smt2_fragment(self, *, instance_suffix: str = "") -> str:
        r = f"sim_r{instance_suffix}"
        c = f"sim_c{instance_suffix}"
        a = f"sim_a{instance_suffix}"
        t = f"sim_t{instance_suffix}"
        lines: list[str] = [
            "; --- agentsim_simplified grounding fragment ---",
            f"(declare-const {r} RefundCall)",
            f"(declare-const {c} Customer)",
            f"(declare-const {a} Account)",
            f"(declare-const {t} Transaction)",
            f"(assert (= (refund-customer {r}) {c}))",
            f"(assert (= (refund-account {r}) {a}))",
            f"(assert (= (refund-transaction {r}) {t}))",
            f"(assert (= (customer-exists-in-db {c}) {str(self.customer_exists_in_db).lower()}))",
            f"(assert (= (account-exists-in-db {a}) {str(self.account_exists_in_db).lower()}))",
            f"(assert (= (transaction-exists-in-db {t}) {str(self.transaction_exists_in_db).lower()}))",
            f"(assert (= (kyc-status {c}) {_kyc(self.customer_kyc)}))",
            f"(assert (= (is-vulnerable {c}) {str(self.customer_vulnerable).lower()}))",
            f"(assert (= (recent-goodwill-credit-total {c}) {self.customer_recent_goodwill_pence}))",
            f"(assert (= (has-sanctions-block {a}) {str(self.account_has_sanctions_block).lower()}))",
            f"(assert (= (transaction-amount {t}) {self.transaction_amount_pence}))",
            f"(assert (= (transaction-status {t}) {_txn_status(self.transaction_status)}))",
            f"(assert (= (refund-type {r}) {_refund_type(self.refund_type)}))",
            f"(assert (= (refund-amount {r}) {self.refund_amount_pence}))",
        ]
        return "\n".join(lines) + "\n"
