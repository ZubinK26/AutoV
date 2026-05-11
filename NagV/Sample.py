from typing import cast, List, Dict, Set, Optional
from nagini_contracts.contracts import Requires, Ensures, Pure, Assert, Implies, Forall, Result

class RefundRequest:
    def __init__(self, 
                 days_since_transaction: int, 
                 unopened_packaging: bool,
                 defective_upon_delivery: bool, 
                 has_proof_of_purchase: bool,
                 is_digital_good: bool, 
                 is_personalized: bool,
                 item_price_cents: int, 
                 shipping_charges_cents: int,
                 merchant_error: bool, 
                 payment_method_accessible: bool,
                 manager_authorized: bool):
        self.days_since_transaction = days_since_transaction
        self.unopened_packaging = unopened_packaging
        self.defective_upon_delivery = defective_upon_delivery
        self.has_proof_of_purchase = has_proof_of_purchase
        self.is_digital_good = is_digital_good
        self.is_personalized = is_personalized
        self.item_price_cents = item_price_cents
        self.shipping_charges_cents = shipping_charges_cents
        self.merchant_error = merchant_error
        self.payment_method_accessible = payment_method_accessible
        self.manager_authorized = manager_authorized

class RefundResult:
    def __init__(self, 
                 is_valid: bool, 
                 refund_amount_cents: int,
                 credit_to_original: bool, 
                 credit_to_store: bool):
        self.is_valid = is_valid
        self.refund_amount_cents = refund_amount_cents
        self.credit_to_original = credit_to_original
        self.credit_to_store = credit_to_store

@Pure
def calculate_item_refund(price: int, unopened: bool, defective: bool) -> int:
    Requires(price >= 0)
    if defective or unopened:
        return price
    return (price * 85) // 100

@Pure
def calculate_shipping_refund(shipping: int, defective: bool, merchant_error: bool) -> int:
    Requires(shipping >= 0)
    if defective or merchant_error:
        return shipping
    return 0

@Requires(req is not None)
@Requires(req.item_price_cents >= 0)
@Requires(req.shipping_charges_cents >= 0)
@Ensures(Result() is not None)
@Ensures(Result().is_valid == (
    req.days_since_transaction <= 30 and 
    req.has_proof_of_purchase and 
    not req.is_digital_good and 
    not req.is_personalized and 
    (calculate_item_refund(req.item_price_cents, req.unopened_packaging, req.defective_upon_delivery) + 
     calculate_shipping_refund(req.shipping_charges_cents, req.defective_upon_delivery, req.merchant_error) <= 50000 or 
     req.manager_authorized)
))
@Ensures(Implies(Result().is_valid, 
                 Result().refund_amount_cents == 
                 calculate_item_refund(req.item_price_cents, req.unopened_packaging, req.defective_upon_delivery) + 
                 calculate_shipping_refund(req.shipping_charges_cents, req.defective_upon_delivery, req.merchant_error)))
@Ensures(Implies(Result().is_valid and req.payment_method_accessible, 
                 Result().credit_to_original and not Result().credit_to_store))
@Ensures(Implies(Result().is_valid and not req.payment_method_accessible, 
                 Result().credit_to_store and not Result().credit_to_original))
@Ensures(Implies(not Result().is_valid, 
                 Result().refund_amount_cents == 0 and 
                 not Result().credit_to_original and 
                 not Result().credit_to_store))
def process_refund(req: RefundRequest) -> RefundResult:
    if req.days_since_transaction > 30:
        return RefundResult(False, 0, False, False)
    
    if not req.has_proof_of_purchase:
        return RefundResult(False, 0, False, False)
        
    if req.is_digital_good or req.is_personalized:
        return RefundResult(False, 0, False, False)

    item_refund = calculate_item_refund(req.item_price_cents, req.unopened_packaging, req.defective_upon_delivery)
    shipping_refund = calculate_shipping_refund(req.shipping_charges_cents, req.defective_upon_delivery, req.merchant_error)
    total_refund = item_refund + shipping_refund

    if total_refund > 50000 and not req.manager_authorized:
        return RefundResult(False, 0, False, False)

    credit_original = req.payment_method_accessible
    credit_store = not req.payment_method_accessible

    return RefundResult(True, total_refund, credit_original, credit_store)