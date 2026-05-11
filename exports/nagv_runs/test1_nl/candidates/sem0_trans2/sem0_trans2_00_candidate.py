from typing import Optional
from nagini_contracts.contracts import Requires, Ensures, Pure, Implies, Result

class RefundRequest:
    """
    Represents the state and attributes of a refund request.
    All monetary values are represented in cents to maintain integer precision.
    """
    def __init__(self, 
                 days_since_transaction: int, 
                 is_unopened: bool, 
                 is_defective: bool, 
                 has_proof_of_purchase: bool, 
                 is_digital_good: bool, 
                 is_personalized: bool, 
                 original_payment_accessible: bool, 
                 is_merchant_error: bool, 
                 transaction_amount_cents: int, 
                 shipping_charges_cents: int, 
                 handling_charges_cents: int, 
                 manager_authorized: bool) -> None:
        self.days_since_transaction = days_since_transaction
        self.is_unopened = is_unopened
        self.is_defective = is_defective
        self.has_proof_of_purchase = has_proof_of_purchase
        self.is_digital_good = is_digital_good
        self.is_personalized = is_personalized
        self.original_payment_accessible = original_payment_accessible
        self.is_merchant_error = is_merchant_error
        self.transaction_amount_cents = transaction_amount_cents
        self.shipping_charges_cents = shipping_charges_cents
        self.handling_charges_cents = handling_charges_cents
        self.manager_authorized = manager_authorized

class RefundResponse:
    """
    Represents the outcome of the refund policy evaluation.
    """
    def __init__(self, 
                 is_valid: bool, 
                 is_approved: bool, 
                 refund_amount_cents: int, 
                 payment_method_is_store_credit: bool) -> None:
        self.is_valid = is_valid
        self.is_approved = is_approved
        self.refund_amount_cents = refund_amount_cents
        self.payment_method_is_store_credit = payment_method_is_store_credit

@Pure
def calculate_potential_refund_total(req: RefundRequest) -> int:
    """
    Calculates the refund total based on deductions for shipping, handling, 
    and restocking fees as defined by the policy.
    """
    # Rules 10 & 11: Shipping and handling are non-refundable unless merchant error or defect
    base_amount = req.transaction_amount_cents
    if not (req.is_merchant_error or req.is_defective):
        base_amount = base_amount - req.shipping_charges_cents - req.handling_charges_cents
    
    # Rule 7: Opened, non-defective items incur a 15% restocking fee
    final_amount = base_amount
    if not req.is_unopened and not req.is_defective:
        # 15% deduction from the current refund total
        final_amount = base_amount - (base_amount * 15 // 100)
        
    return final_amount if final_amount > 0 else 0

@Pure
def check_approval_conditions(req: RefundRequest, calculated_amount: int) -> bool:
    """
    Evaluates the boolean conditions required for a refund to be approved.
    """
    # Rule 1: Must be within 30 days (validity condition)
    if req.days_since_transaction > 30:
        return False
    
    # Rule 4: Must have verifiable proof of purchase
    if not req.has_proof_of_purchase:
        return False
    
    # Rule 5: Digital goods are non-refundable
    if req.is_digital_good:
        return False
    
    # Rule 6: Personalized items are non-refundable
    if req.is_personalized:
        return False
    
    # Rule 2 & 3: Full refunds require original packaging unless defective
    is_full_refund = (calculated_amount == req.transaction_amount_cents)
    if is_full_refund and not (req.is_unopened or req.is_defective):
        return False
        
    # Rule 12: Managerial authorization for refunds exceeding $500
    if calculated_amount > 50000 and not req.manager_authorized:
        return False
        
    return True

@Requires(req.transaction_amount_cents >= 0)
@Requires(req.shipping_charges_cents >= 0)
@Requires(req.handling_charges_cents >= 0)
@Requires(req.transaction_amount_cents >= (req.shipping_charges_cents + req.handling_charges_cents))
@Ensures(Result().is_valid == (req.days_since_transaction <= 30))
@Ensures(Implies(Result().is_approved, req.has_proof_of_purchase))
@Ensures(Implies(req.is_digital_good or req.is_personalized, not Result().is_approved))
@Ensures(Implies(Result().is_approved and Result().refund_amount_cents == req.transaction_amount_cents, req.is_unopened or req.is_defective))
@Ensures(Implies(Result().is_approved and not req.is_unopened and not req.is_defective, Result().refund_amount_cents <= (req.transaction_amount_cents * 85 // 100)))
@Ensures(Implies(Result().is_approved, Result().payment_method_is_store_credit == (not req.original_payment_accessible)))
@Ensures(Implies(Result().is_approved and not (req.is_merchant_error or req.is_defective), Result().refund_amount_cents <= (req.transaction_amount_cents - req.shipping_charges_cents - req.handling_charges_cents)))
@Ensures(Implies(Result().is_approved and Result().refund_amount_cents > 50000, req.manager_authorized))
@Ensures(Result().is_approved == (Result().is_valid and check_approval_conditions(req, calculate_potential_refund_total(req))))
def process_refund_request(req: RefundRequest) -> RefundResponse:
    """
    Translates the NL refund policy into a formal decision logic.
    """
    valid = (req.days_since_transaction <= 30)
    potential_amount = calculate_potential_refund_total(req)
    approved = valid and check_approval_conditions(req, potential_amount)
    
    final_amount = potential_amount if approved else 0
    store_credit = approved and not req.original_payment_accessible
    
    return RefundResponse(
        is_valid=valid,
        is_approved=approved,
        refund_amount_cents=final_amount,
        payment_method_is_store_credit=store_credit
    )