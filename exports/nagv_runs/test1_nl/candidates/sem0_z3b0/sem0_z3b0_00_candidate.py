from z3 import *

def run_z3_check():
    solver = Solver()

    # Variables
    is_valid = Bool('is_valid')
    days_since_transaction = Int('days_since_transaction')
    is_full_refund = Bool('is_full_refund')
    is_original_unopened_packaging = Bool('is_original_unopened_packaging')
    is_defective_upon_delivery = Bool('is_defective_upon_delivery')
    has_verifiable_proof_of_purchase = Bool('has_verifiable_proof_of_purchase')
    is_digital_good = Bool('is_digital_good')
    is_refundable = Bool('is_refundable')
    is_personalized_item = Bool('is_personalized_item')
    is_opened = Bool('is_opened')
    is_defective = Bool('is_defective')
    restocking_fee_applied = Bool('restocking_fee_applied')
    is_approved = Bool('is_approved')
    credited_to_original_payment = Bool('credited_to_original_payment')
    original_payment_inaccessible = Bool('original_payment_inaccessible')
    is_store_credit = Bool('is_store_credit')
    is_merchant_error = Bool('is_merchant_error')
    is_defect = Bool('is_defect')
    shipping_charges_refundable = Bool('shipping_charges_refundable')
    handling_charges_refundable = Bool('handling_charges_refundable')
    is_executed = Bool('is_executed')
    refund_total = Int('refund_total')
    has_managerial_authorization = Bool('has_managerial_authorization')

    # Constraints

    # nl#1: Every refund request is valid if and only if initiated within 30 days
    solver.assert_and_track(is_valid == (days_since_transaction <= 30), "nl#1")

    # nl#2 & nl#3: Full refund requires original packaging unless defective upon delivery
    # "If full refund, then (packaging OR defective_upon_delivery)"
    solver.assert_and_track(
        Implies(is_full_refund, Or(is_original_unopened_packaging, is_defective_upon_delivery)),
        "nl#2_nl#3"
    )

    # nl#4: Every refund request is accompanied by a verifiable proof of purchase
    solver.assert_and_track(has_verifiable_proof_of_purchase == True, "nl#4")

    # nl#5: Every digital good is strictly non-refundable
    solver.assert_and_track(Implies(is_digital_good, Not(is_refundable)), "nl#5")

    # nl#6: Every personalized item is strictly non-refundable
    solver.assert_and_track(Implies(is_personalized_item, Not(is_refundable)), "nl#6")

    # nl#7: Every opened, non-defective item is subject to a 15% restocking fee
    solver.assert_and_track(
        Implies(And(is_opened, Not(is_defective)), restocking_fee_applied),
        "nl#7"
    )

    # nl#8 & nl#9: Approved refund payment method logic
    # Exclusively original payment unless inaccessible, then store credit
    solver.assert_and_track(
        Implies(is_approved, And(
            is_store_credit == original_payment_inaccessible,
            credited_to_original_payment == Not(original_payment_inaccessible)
        )),
        "nl#8_nl#9"
    )

    # nl#10: Shipping charges non-refundable unless merchant error or defect
    solver.assert_and_track(
        Implies(Not(Or(is_merchant_error, is_defect)), Not(shipping_charges_refundable)),
        "nl#10"
    )

    # nl#11: Handling charges non-refundable unless merchant error or defect
    solver.assert_and_track(
        Implies(Not(Or(is_merchant_error, is_defect)), Not(handling_charges_refundable)),
        "nl#11"
    )

    # nl#12: Refund > $500 requires managerial authorization
    solver.assert_and_track(
        Implies(And(is_executed, refund_total > 500), has_managerial_authorization),
        "nl#12"
    )

    # Check satisfiability
    status = solver.check()
    result = {"status": str(status).lower()}

    if status == sat:
        model = solver.model()
        # Correctly iterate over model declarations to create an excerpt
        decls = model.decls()
        excerpt = [f"{d.name()}={model[d]}" for d in decls[:10]]
        result["model_excerpt"] = ", ".join(excerpt)
    elif status == unsat:
        core = solver.unsat_core()
        result["unsat_core"] = [str(c) for c in core]

    return result

if __name__ == "__main__":
    print(run_z3_check())