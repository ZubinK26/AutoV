from dataclasses import dataclass
from nagini_contracts.contracts import Requires, Ensures, Pure, Result

@dataclass
class RefundRequest:
    days_since_transaction: int
    original_packaging: bool
    is_defective: bool
    has_proof_of_purchase: bool
    is_digital_good: bool
    is_personalized: bool
    original_payment_accessible: bool
    merchant_error: bool
    refund_amount: int
    manager_authorized: bool

@dataclass
class RefundResult:
    is_approved: bool
    restocking_fee_applied: bool
    credit_to_store: bool
    refund_shipping: bool

@Pure
def is_eligible(req: RefundRequest) -> bool:
    return (
        req.days_since_transaction <= 30 and
        req.has_proof_of_purchase and
        not req.is_digital_good and
        not req.is_personalized
    )

@Pure
def is_fully_approved(req: RefundRequest) -> bool:
    return is_eligible(req) and (req.refund_amount <= 500 or req.manager_authorized)

@Requires(req is not None)
@Ensures(Result() is not None)
@Ensures(Result().is_approved == is_fully_approved(req))
@Ensures(Result().restocking_fee_applied == (Result().is_approved and not req.original_packaging and not req.is_defective))
@Ensures(Result().credit_to_store == (Result().is_approved and not req.original_payment_accessible))
@Ensures(Result().refund_shipping == (Result().is_approved and (req.merchant_error or req.is_defective)))
def process_refund(req: RefundRequest) -> RefundResult:
    approved = is_fully_approved(req)
    
    restocking_fee = False
    store_credit = False
    shipping_refund = False
    
    if approved:
        if not req.original_packaging and not req.is_defective:
            restocking_fee = True
            
        if not req.original_payment_accessible:
            store_credit = True
            
        if req.merchant_error or req.is_defective:
            shipping_refund = True
            
    return RefundResult(
        is_approved=approved,
        restocking_fee_applied=restocking_fee,
        credit_to_store=store_credit,
        refund_shipping=shipping_refund
    )