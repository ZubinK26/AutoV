from dataclasses import dataclass
from typing import cast, List, Dict, Set, Optional
from nagini_contracts.contracts import Requires, Ensures, Pure, Assert, Implies, Result

@dataclass
class RefundRequest:
    days_since_purchase: int
    is_full_refund: bool
    is_unopened: bool
    is_defective: bool
    has_proof_of_purchase: bool
    is_digital: bool
    is_personalized: bool
    original_payment_accessible: bool
    is_merchant_error: bool
    transaction_amount: int  # Amount in cents
    shipping_charges: int     # Amount in cents
    handling_charges: int     # Amount in cents
    has_manager_auth: bool

@dataclass
class RefundResponse:
    is_valid: bool
    is_approved: bool
    refund_amount: int
    is_store_credit: bool

@Pure
def calculate_potential_amount(request: RefundRequest) -> int:
    """Calculates the refund total based on shipping, handling, and restocking fees."""
    # Rule 10 & 11: Shipping and handling are non-refundable if not merchant error or defect
    base_amount = request.transaction_amount
    if not (request.is_merchant_error or request.is_defective):
        base_amount = base_amount - request.shipping_charges - request.handling_charges
    
    # Rule 7: 15% restocking fee for opened, non-defective items
    if not request.is_unopened and not request.is_defective:
        # Apply 15% restocking fee (keep 85%)
        return (base_amount * 85) // 100
    
    return base_amount

@Requires(lambda request: request.transaction_amount >= 0)
@Requires(lambda request: request.shipping_charges >= 0)
@Requires(lambda request: request.handling_charges >= 0)
@Requires(lambda request: request.days_since_purchase >= 0)
@Ensures(lambda request: Result().is_valid == (request.days_since_purchase <= 30))
@Ensures(lambda request: Implies(Result().is_approved, Result().is_valid))
@Ensures(lambda request: Implies(Result().is_approved, request.has_proof_of_purchase))
@Ensures(lambda request: Implies(request.is_digital, not Result().is_approved))
@Ensures(lambda request: Implies(request.is_personalized, not Result().is_approved))
@Ensures(lambda request: Implies(Result().is_approved and request.is_full_refund and not request.is_defective, request.is_unopened))
@Ensures(lambda request: Implies(Result().is_approved and Result().refund_amount > 50000, request.has_manager_auth))
@Ensures(lambda request: Implies(Result().is_approved, Result().is_store_credit == (not request.original_payment_accessible)))
@Ensures(lambda request: Implies(Result().is_approved, Result().refund_amount == calculate_potential_amount(request)))
def process_refund_request(request: RefundRequest) -> RefundResponse:
    # Rule 1: Validity check (if and only if within 30 days)
    is_valid = request.days_since_purchase <= 30
    
    # Rule 4, 5, 6: Basic eligibility
    # Every refund request is accompanied by proof of purchase.
    # Digital and personalized items are strictly non-refundable.
    if not is_valid or not request.has_proof_of_purchase or request.is_digital or request.is_personalized:
        return RefundResponse(is_valid, False, 0, False)
    
    # Calculate the refund total based on Rules 7, 10, and 11
    refund_total = calculate_potential_amount(request)
    
    # Rule 2 & 3: Packaging requirements for full refunds
    # Defective items are exempt from the unopened packaging requirement.
    if request.is_full_refund and not request.is_defective:
        if not request.is_unopened:
            return RefundResponse(is_valid, False, 0, False)
            
    # Rule 12: Managerial authorization for refunds exceeding $500 (50,000 cents)
    if refund_total > 50000:
        if not request.has_manager_auth:
            return RefundResponse(is_valid, False, 0, False)
            
    # Rule 8 & 9: Payment method determination
    # Credited to original payment method unless inaccessible, then store credit.
    is_store_credit = not request.original_payment_accessible
    
    return RefundResponse(
        is_valid=is_valid,
        is_approved=True,
        refund_amount=refund_total,
        is_store_credit=is_store_credit
    )