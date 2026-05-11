from dataclasses import dataclass
from nagini_contracts.contracts import Requires, Ensures, Pure, Assert, Implies, Result


@dataclass
class RefundRequest:
    days_since_transaction: int       # days elapsed since original transaction
    is_full_refund: bool
    item_returned_in_original_packaging: bool
    item_verified_defective_on_delivery: bool
    has_proof_of_purchase: bool
    is_digital_good: bool
    is_personalized_item: bool
    is_item_opened: bool              # True if item has been opened
    original_payment_method_accessible: bool
    return_due_to_merchant_error_or_defect: bool
    refund_total_cents: int           # refund total in cents (integer arithmetic)
    has_managerial_authorization: bool


@dataclass
class RefundDecision:
    is_valid: bool
    is_approved: bool
    restocking_fee_applies: bool      # 15% restocking fee applies
    credited_to_original_payment: bool
    credited_as_store_credit: bool
    shipping_charges_refundable: bool
    handling_charges_refundable: bool
    requires_managerial_authorization: bool


@Pure
def packaging_requirement_satisfied(req: RefundRequest) -> bool:
    Requires(req is not None)
    # If full refund: item must be in original unopened packaging,
    # UNLESS item is verified defective on delivery.
    if req.is_full_refund:
        if req.item_verified_defective_on_delivery:
            return True
        else:
            return req.item_returned_in_original_packaging
    else:
        return True


@Pure
def is_refundable_item(req: RefundRequest) -> bool:
    Requires(req is not None)
    # Digital goods and personalized items are strictly non-refundable.
    if req.is_digital_good:
        return False
    if req.is_personalized_item:
        return False
    return True


@Pure
def restocking_fee_applies(req: RefundRequest) -> bool:
    Requires(req is not None)
    # 15% restocking fee applies to opened, non-defective items.
    return req.is_item_opened and not req.item_verified_defective_on_delivery


@Pure
def shipping_refundable(req: RefundRequest) -> bool:
    Requires(req is not None)
    return req.return_due_to_merchant_error_or_defect


@Pure
def handling_refundable(req: RefundRequest) -> bool:
    Requires(req is not None)
    return req.return_due_to_merchant_error_or_defect


@Pure
def managerial_auth_required(req: RefundRequest) -> bool:
    Requires(req is not None)
    # Managerial authorization required if refund total exceeds $500 (50000 cents).
    return req.refund_total_cents > 50000


@Pure
def request_is_valid(req: RefundRequest) -> bool:
    Requires(req is not None)
    # Valid iff: within 30 days, has proof of purchase, item is refundable,
    # and packaging requirement is satisfied.
    if req.days_since_transaction < 0:
        return False
    if req.days_since_transaction > 30:
        return False
    if not req.has_proof_of_purchase:
        return False
    if not is_refundable_item(req):
        return False
    if not packaging_requirement_satisfied(req):
        return False
    return True


@Pure
def credit_to_original_payment(req: RefundRequest) -> bool:
    Requires(req is not None)
    return req.original_payment_method_accessible


@Pure
def credit_as_store_credit(req: RefundRequest) -> bool:
    Requires(req is not None)
    return not req.original_payment_method_accessible


def evaluate_refund(req: RefundRequest) -> RefundDecision:
    Requires(req is not None)
    Requires(req.days_since_transaction >= 0)
    Requires(req.refund_total_cents >= 0)
    # Validity postconditions
    Ensures(Implies(
        Result().is_valid,
        req.days_since_transaction <= 30
    ))
    Ensures(Implies(
        Result().is_valid,
        req.has_proof_of_purchase
    ))
    Ensures(Implies(
        Result().is_valid,
        not req.is_digital_good
    ))
    Ensures(Implies(
        Result().is_valid,
        not req.is_personalized_item
    ))
    # Full refund packaging rule
    Ensures(Implies(
        Result().is_valid and req.is_full_refund and not req.item_verified_defective_on_delivery,
        req.item_returned_in_original_packaging
    ))
    # Restocking fee postcondition
    Ensures(Implies(
        Result().is_approved,
        Result().restocking_fee_applies == (req.is_item_opened and not req.item_verified_defective_on_delivery)
    ))
    # Credit method postconditions
    Ensures(Implies(
        Result().is_approved,
        Result().credited_to_original_payment == req.original_payment_method_accessible
    ))
    Ensures(Implies(
        Result().is_approved,
        Result().credited_as_store_credit == (not req.original_payment_method_accessible)
    ))
    # Shipping/handling postconditions
    Ensures(Implies(
        Result().is_approved,
        Result().shipping_charges_refundable == req.return_due_to_merchant_error_or_defect
    ))
    Ensures(Implies(
        Result().is_approved,
        Result().handling_charges_refundable == req.return_due_to_merchant_error_or_defect
    ))
    # Managerial authorization postcondition
    Ensures(Implies(
        Result().is_approved and req.refund_total_cents > 50000,
        Result().requires_managerial_authorization
    ))
    # Non-refundable items must not be approved
    Ensures(Implies(
        req.is_digital_good or req.is_personalized_item,
        not Result().is_approved
    ))

    valid = request_is_valid(req)

    # An approved refund requires validity; if managerial auth is required, it must be present.
    auth_required = managerial_auth_required(req)
    approved = valid and (not auth_required or req.has_managerial_authorization)

    fee_applies = restocking_fee_applies(req)
    to_original = credit_to_original_payment(req)
    to_store_credit = credit_as_store_credit(req)
    ship_refundable = shipping_refundable(req)
    hand_refundable = handling_refundable(req)

    return RefundDecision(
        is_valid=valid,
        is_approved=approved,
        restocking_fee_applies=fee_applies,
        credited_to_original_payment=to_original,
        credited_as_store_credit=to_store_credit,
        shipping_charges_refundable=ship_refundable,
        handling_charges_refundable=hand_refundable,
        requires_managerial_authorization=auth_required
    )