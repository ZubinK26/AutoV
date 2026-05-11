from z3 import *

def run_z3_check():
    """
    Translates the refund policy ruleset into Z3 constraints and checks for consistency.
    """
    solver = Solver()

    # --- Variables ---
    # Time and Money
    days_since_transaction = Int('days_since_transaction')
    refund_total = Int('refund_total')  # Represented in dollars (or cents)

    # Status Booleans
    is_valid = Bool('is_valid')
    is_approved = Bool('is_approved')
    is_full_refund = Bool('is_full_refund')

    # Item Properties
    is_original_packaging = Bool('is_original_packaging')
    is_opened = Bool('is_opened')
    is_defective = Bool('is_defective')
    is_digital_good = Bool('is_digital_good')
    is_personalized = Bool('is_personalized')

    # Request/Process Properties
    has_proof_of_purchase = Bool('has_proof_of_purchase')
    restocking_fee_applied = Bool('restocking_fee_applied')
    is_merchant_error = Bool('is_merchant_error')
    shipping_refunded = Bool('shipping_refunded')
    handling_refunded = Bool('handling_refunded')
    has_managerial_auth = Bool('has_managerial_auth')

    # Payment Method Properties
    original_payment_method_accessible = Bool('original_payment_method_accessible')
    refund_to_original_method = Bool('refund_to_original_method')
    refund_to_store_credit = Bool('refund_to_store_credit')

    # --- Constraints (Policy Rules) ---

    # Rule 1: Every refund request is valid if and only if initiated within 30 days.
    solver.assert_and_track(is_valid == (days_since_transaction <= 30), "r1_valid_iff_30_days")

    # Rule 2 & 3: Full refund packaging requirements and defective exception.
    # Rule 2: If full refund, then original, unopened packaging.
    # Rule 3: If defective, then original, unopened packaging is not required.
    # Logic: If it's a full refund and NOT defective, it MUST be in original, unopened packaging.
    solver.assert_and_track(Implies(And(is_full_refund, Not(is_defective)), 
                                    And(is_original_packaging, Not(is_opened))), "r2_3_full_refund_packaging")

    # Rule 4: Every refund request is accompanied by a verifiable proof of purchase.
    # We interpret this as a necessary condition for any request to be processed/approved.
    solver.assert_and_track(has_proof_of_purchase == True, "r4_proof_of_purchase_mandatory")

    # Rule 5: Every digital good is strictly non-refundable.
    solver.assert_and_track(Implies(is_digital_good, Not(is_approved)), "r5_digital_non_refundable")

    # Rule 6: Every personalized item is strictly non-refundable.
    solver.assert_and_track(Implies(is_personalized, Not(is_approved)), "r6_personalized_non_refundable")

    # Rule 7: Every opened, non-defective item is subject to a 15% restocking fee deducted from the refund total.
    solver.assert_and_track(Implies(And(is_opened, Not(is_defective)), restocking_fee_applied), "r7_restocking_fee")

    # Rule 8 & 9: Payment method logic.
    # Rule 8: Approved refund credited exclusively to original payment method.
    # Rule 9: If inaccessible, defaults to non-transferable store credit.
    solver.assert_and_track(
        Implies(is_approved, 
                If(original_payment_method_accessible, 
                   And(refund_to_original_method, Not(refund_to_store_credit)), 
                   And(refund_to_store_credit, Not(refund_to_original_method)))), 
        "r8_9_payment_method_logic"
    )

    # Rule 10 & 11: Shipping and handling non-refundable unless merchant error or defect.
    solver.assert_and_track(Implies(Not(Or(is_merchant_error, is_defective)), 
                                    And(Not(shipping_refunded), Not(handling_refunded))), "r10_11_fees_non_refundable")

    # Rule 12: If refund executed and total > $500, then managerial authorization.
    solver.assert_and_track(Implies(And(is_approved, refund_total > 500), has_managerial_auth), "r12_managerial_auth")

    # --- Implicit Logical Constraints ---
    
    # Approval requires a valid request.
    solver.assert_and_track(Implies(is_approved, is_valid), "approval_requires_validity")
    
    # A full refund is a specific type of approved refund.
    solver.assert_and_track(Implies(is_full_refund, is_approved), "full_implies_approved")

    # If a restocking fee is deducted or shipping/handling is not refunded, it is not a "full" refund.
    solver.assert_and_track(Implies(restocking_fee_applied, Not(is_full_refund)), "restocking_deduction_not_full")
    solver.assert_and_track(Implies(Not(shipping_refunded), Not(is_full_refund)), "shipping_deduction_not_full")
    solver.assert_and_track(Implies(Not(handling_refunded), Not(is_full_refund)), "handling_deduction_not_full")

    # --- Execution ---
    status = solver.check()
    result = {"status": str(status).lower()}

    if status == sat:
        # Provide a small excerpt of a valid scenario
        model = solver.model()
        excerpt = [f"{v}: {model[v]}" for v in [is_approved, is_full_refund, is_valid, refund_total] if v in model]
        result["model_excerpt"] = ", ".join(excerpt)
    elif status == unsat:
        # Provide the labels of the conflicting rules
        result["unsat_core"] = [str(c) for c in solver.unsat_core()]

    return result

if __name__ == "__main__":
    print(run_z3_check())