from dataclasses import dataclass
from typing import cast
from nagini_contracts.contracts import Requires, Ensures, Pure, Assert, Implies, Result


@dataclass
class RefundRequest:
    days_since_transaction: int
    is_full_refund: bool
    returned_in_original_packaging: bool
    verified_defective: bool
    has_proof_of_purchase: bool
    is_digital_good: bool
    is_personalized_item: bool
    is_opened: bool
    merchant_error: bool
    original_payment_accessible: bool
    managerial_authorization: bool
    base_refund_cents: int  # pre-fee, pre-shipping refund principal
    original_shipping_cents: int
    original_handling_cents: int


# Line 0: timeframe validity
@Pure
def is_within_timeframe(r: RefundRequest) -> bool:
    Requires(r.days_since_transaction >= 0)
    Ensures(Result() == (r.days_since_transaction <= 30))
    return r.days_since_transaction <= 30


# Lines 1 & 2: packaging requirement, with defective override
@Pure
def packaging_requirement_satisfied(r: RefundRequest) -> bool:
    Ensures(Result() == ((not r.is_full_refund) or r.returned_in_original_packaging or r.verified_defective))
    if not r.is_full_refund:
        return True
    if r.verified_defective:
        return True
    return r.returned_in_original_packaging


# Lines 4 & 5: categorical non-refundability
@Pure
def is_categorically_non_refundable(r: RefundRequest) -> bool:
    Ensures(Result() == (r.is_digital_good or r.is_personalized_item))
    return r.is_digital_good or r.is_personalized_item


# Eligibility: lines 0, 1, 2, 3, 4, 5
@Pure
def is_eligible(r: RefundRequest) -> bool:
    Requires(r.days_since_transaction >= 0)
    Ensures(Result() == (
        is_within_timeframe(r)
        and r.has_proof_of_purchase
        and (not is_categorically_non_refundable(r))
        and packaging_requirement_satisfied(r)
    ))
    return (
        is_within_timeframe(r)
        and r.has_proof_of_purchase
        and (not is_categorically_non_refundable(r))
        and packaging_requirement_satisfied(r)
    )


# Line 6: 15% restocking fee for opened, non-defective items
@Pure
def restocking_fee_applies(r: RefundRequest) -> bool:
    Ensures(Result() == (r.is_opened and (not r.verified_defective)))
    return r.is_opened and (not r.verified_defective)


@Pure
def apply_restocking(base_cents: int, fee_applies: bool) -> int:
    Requires(base_cents >= 0)
    Ensures(Implies(fee_applies, Result() == (base_cents * 85) // 100))
    Ensures(Implies(not fee_applies, Result() == base_cents))
    Ensures(Result() >= 0)
    if fee_applies:
        return (base_cents * 85) // 100
    return base_cents


# Lines 9 & 10: shipping and handling refundability
@Pure
def shipping_and_handling_refundable(r: RefundRequest) -> bool:
    Ensures(Result() == (r.merchant_error or r.verified_defective))
    return r.merchant_error or r.verified_defective


@Pure
def compute_refund_total_cents(r: RefundRequest) -> int:
    Requires(r.base_refund_cents >= 0)
    Requires(r.original_shipping_cents >= 0)
    Requires(r.original_handling_cents >= 0)
    Ensures(Result() >= 0)
    item_part = apply_restocking(r.base_refund_cents, restocking_fee_applies(r))
    if shipping_and_handling_refundable(r):
        return item_part + r.original_shipping_cents + r.original_handling_cents
    return item_part


# Line 11: managerial authorization required for refunds exceeding $500 (50000 cents)
@Pure
def managerial_auth_satisfied(r: RefundRequest) -> bool:
    Requires(r.base_refund_cents >= 0)
    Requires(r.original_shipping_cents >= 0)
    Requires(r.original_handling_cents >= 0)
    Ensures(Result() == ((compute_refund_total_cents(r) <= 50000) or r.managerial_authorization))
    return (compute_refund_total_cents(r) <= 50000) or r.managerial_authorization


# Final approval decision
@Pure
def is_approved(r: RefundRequest) -> bool:
    Requires(r.days_since_transaction >= 0)
    Requires(r.base_refund_cents >= 0)
    Requires(r.original_shipping_cents >= 0)
    Requires(r.original_handling_cents >= 0)
    Ensures(Result() == (is_eligible(r) and managerial_auth_satisfied(r)))
    # Line 4 & 5: digital/personalized => never approved
    Ensures(Implies(r.is_digital_good, not Result()))
    Ensures(Implies(r.is_personalized_item, not Result()))
    # Line 0: out of timeframe => not approved
    Ensures(Implies(r.days_since_transaction > 30, not Result()))
    # Line 3: missing proof => not approved
    Ensures(Implies(not r.has_proof_of_purchase, not Result()))
    # Line 11: large refund without managerial auth => not approved
    Ensures(Implies(Result() and compute_refund_total_cents(r) > 50000, r.managerial_authorization))
    return is_eligible(r) and managerial_auth_satisfied(r)


# Lines 7 & 8: payment destination for approved refunds
@Pure
def credited_to_original_payment(r: RefundRequest) -> bool:
    Requires(r.days_since_transaction >= 0)
    Requires(r.base_refund_cents >= 0)
    Requires(r.original_shipping_cents >= 0)
    Requires(r.original_handling_cents >= 0)
    Ensures(Result() == (is_approved(r) and r.original_payment_accessible))
    return is_approved(r) and r.original_payment_accessible


@Pure
def credited_as_store_credit(r: RefundRequest) -> bool:
    Requires(r.days_since_transaction >= 0)
    Requires(r.base_refund_cents >= 0)
    Requires(r.original_shipping_cents >= 0)
    Requires(r.original_handling_cents >= 0)
    Ensures(Result() == (is_approved(r) and (not r.original_payment_accessible)))
    return is_approved(r) and (not r.original_payment_accessible)