from typing import cast, List, Dict, Set, Optional
from nagini_contracts.contracts import Requires, Ensures, Pure, Assert, Implies, Forall, Result

class RefundRequest:
    def __init__(self, 
                 days_since_transaction: int,
                 is_unopened: bool,
                 is_defective: bool,
                 has_proof_of_purchase: bool,
                 is_digital_good: bool,
                 is_personalized: bool,
                 refund_total: int,
                 original_payment_accessible: bool,
                 merchant_error: bool,
                 managerial_authorization: bool):
        self.days_since_transaction = days_since_transaction
        self.is_unopened = is_unopened
        self.is_defective = is_defective
        self.has_proof_of_purchase = has_proof_of_purchase
        self.is_digital_good = is_digital_good
        self.is_personalized = is_personalized
        self.refund_total = refund_total
        self.original_payment_accessible = original_payment_accessible
        self.merchant_error = merchant_error
        self.managerial_authorization = managerial_authorization

class RefundResult:
    def __init__(self,
                 is_valid: bool,
                 is_refundable: bool,
                 is_full_refund: bool,
                 restocking_fee_applied: bool,
                 credited_to_original_payment: bool,
                 credited_to_store_credit: bool,
                 shipping_refundable: bool,
                 handling_refundable: bool,
                 refund_executed: bool,
                 final_refund_total: int):
        self.is_valid = is_valid
        self.is_refundable = is_refundable
        self.is_full_refund = is_full_refund
        self.restocking_fee_applied = restocking_fee_applied
        self.credited_to_original_payment = credited_to_original_payment
        self.credited_to_store_credit = credited_to_store_credit
        self.shipping_refundable = shipping_refundable
        self.handling_refundable = handling_refundable
        self.refund_executed = refund_executed
        self.final_refund_total = final_refund_total

@Requires(req.has_proof_of_purchase)
@Ensures(Result().is_valid == (req.days_since_transaction <= 30))
@Ensures(Implies(Result().is_full_refund, req.is_unopened or req.is_defective))
@Ensures(Implies(req.is_digital_good, not Result().is_refundable))
@Ensures(Implies(req.is_personalized, not Result().is_refundable))
@Ensures(Implies(not req.is_unopened and not req.is_defective, Result().restocking_fee_applied))
@Ensures(Implies(Result().restocking_fee_applied, Result().final_refund_total == req.refund_total * 85 // 100))
@Ensures(Implies(not Result().restocking_fee_applied, Result().final_refund_total == req.refund_total))
@Ensures(Implies(Result().refund_executed and req.original_payment_accessible, Result().credited_to_original_payment and not Result().credited_to_store_credit))
@Ensures(Implies(Result().refund_executed and not req.original_payment_accessible, Result().credited_to_store_credit and not Result().credited_to_original_payment))
@Ensures(Implies(not req.merchant_error and not req.is_defective, not Result().shipping_refundable))
@Ensures(Implies(not req.merchant_error and not req.is_defective, not Result().handling_refundable))
@Ensures(Implies(Result().refund_executed and req.refund_total > 500, req.managerial_authorization))
def process_refund(req: RefundRequest) -> RefundResult:
    is_valid = req.days_since_transaction <= 30
    is_refundable = not req.is_digital_good and not req.is_personalized
    
    refund_executed = is_valid and is_refundable
    
    if refund_executed and req.refund_total > 500 and not req.managerial_authorization:
        refund_executed = False
        
    is_full_refund = refund_executed and (req.is_unopened or req.is_defective)
    restocking_fee_applied = not req.is_unopened and not req.is_defective
    
    if restocking_fee_applied:
        final_refund_total = req.refund_total * 85 // 100
    else:
        final_refund_total = req.refund_total
    
    credited_to_original_payment = refund_executed and req.original_payment_accessible
    credited_to_store_credit = refund_executed and not req.original_payment_accessible
    
    shipping_refundable = req.merchant_error or req.is_defective
    handling_refundable = req.merchant_error or req.is_defective
    
    return RefundResult(
        is_valid,
        is_refundable,
        is_full_refund,
        restocking_fee_applied,
        credited_to_original_payment,
        credited_to_store_credit,
        shipping_refundable,
        handling_refundable,
        refund_executed,
        final_refund_total
    )