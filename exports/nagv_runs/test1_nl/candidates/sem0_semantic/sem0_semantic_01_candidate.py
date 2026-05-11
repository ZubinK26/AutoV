from z3 import *

def run_z3_check():
    solver = Solver()

    # Variables
    is_valid = Bool('is_valid')
    days_since_transaction = Int('days_since_transaction')
    is_full_refund = Bool('is_full_refund')
    is_original_unopened_packaging = Bool('is_original_unopened_packaging')
    is_defective = Bool('is_defective') # Consolidated: covers delivery, general defect, and non-defective
    has_verifiable_proof_of_purchase = Bool('has_verifiable_proof_of_purchase')
    is_digital_good = Bool('is_digital_good')
    is_refundable = Bool('is_refundable')
    is_personalized_item = Bool('is_personalized_item')
    is_opened = Bool('is_opened')
    is_approved = Bool('is_approved')
    credited_to_original_payment = Bool('credited_to_original_payment')
    original_payment_inaccessible = Bool('original_payment_inaccessible')
    is_store_credit = Bool('is_store_credit')
    is_merchant_error = Bool('is_merchant_error')
    shipping_charges_refundable = Bool('shipping_charges_refundable')
    handling_charges_refundable = Bool('handling_charges_refundable')
    is_executed = Bool('is_executed')
    base_amount = Real('base_amount')
    refund_total = Real('refund_total')
    has_managerial_authorization = Bool('has_managerial_authorization')

    # Domain Constraints
    solver.add(base_amount > 0)
    solver.add(days_since_transaction >= 0)

    # nl#1: Every refund request is valid if and only if initiated within 30 days
    solver.assert_and_track(is_valid == (days_since_transaction <= 30), "nl#1")

    # nl#5 & nl#6: Refundability logic
    solver.assert_and_track(is_refundable == And(Not(is_digital_good), Not(is_personalized_item)), "nl#5_nl#6")

    # nl#4 & Progression: Approved requires valid, refundable, and proof
    # This links NL#1, NL#4, NL#5, NL#6
    solver.assert_and_track(
        Implies(is_approved, And(is_valid, is_refundable, has_verifiable_proof_of_purchase)),
        "nl#4_progression"
    )

    # nl#7: 15% restocking fee logic (Mathematical deduction)
    # If opened and not defective, total is 85% of base. Otherwise, it's the base.
    restocking_fee_applies = And(is_opened, Not(is_defective))
    solver.assert_and_track(
        refund_total == If(restocking_fee_applies, base_amount * 0.85, base_amount),
        "nl#7"
    )

    # nl#2 & nl#3: Full refund packaging requirements
    # Define full refund as no deductions
    solver.add(is_full_refund == (refund_total == base_amount))
    solver.assert_and_track(
        Implies(is_full_refund, Or(is_original_unopened_packaging, is_defective)),
        "nl#2_nl#3"
    )

    # nl#8 & nl#9: Payment method logic
    solver.assert_and_track(
        Implies(is_approved, And(
            is_store_credit == original_payment_inaccessible,
            credited_to_original_payment == Not(original_payment_inaccessible)
        )),
        "nl#8_nl#9"
    )

    # nl#10 & nl#11: Shipping/Handling charges
    solver.assert_and_track(
        Implies(Not(Or(is_merchant_error, is_defective)), 
                And(Not(shipping_charges_refundable), Not(handling_charges_refundable))),
        "nl#10_nl#11"
    )