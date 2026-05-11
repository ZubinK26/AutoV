from z3 import *

def run_z3_check():
    solver = Solver()

    # Variables
    valid_request = Bool('valid_request')
    days_since_transaction = Int('days_since_transaction')
    is_full_refund = Bool('is_full_refund')
    item_in_original_packaging = Bool('item_in_original_packaging')
    verified_defective = Bool('verified_defective')
    refund_request_exists = Bool('refund_request_exists')
    proof_of_purchase = Bool('proof_of_purchase')
    is_digital_good = Bool('is_digital_good')
    is_refundable = Bool('is_refundable')
    is_personalized_item = Bool('is_personalized_item')
    is_opened = Bool('is_opened')
    restocking_fee_applied = Bool('restocking_fee_applied')
    approved_refund = Bool('approved_refund')
    credited_to_original_method = Bool('credited_to_original_method')
    store_credit = Bool('store_credit')
    original_method_inaccessible = Bool('original_method_inaccessible')
    merchant_error = Bool('merchant_error')
    shipping_charges_refundable = Bool('shipping_charges_refundable')
    handling_charges_refundable = Bool('handling_charges_refundable')
    refund_executed = Bool('refund_executed')
    refund_total = Int('refund_total')
    managerial_authorization = Bool('managerial_authorization')

    # Constraints

    # nl#1: Every refund request is valid if and only if initiated within 30 days.
    solver.assert_and_track(
        valid_request == (days_since_transaction <= 30),
        "nl#1_validity_period"
    )

    # nl#2 & nl#3: Full refund requires original packaging unless item is defective.
    # "Not required" in nl#3 qualifies the obligation in nl#2.
    solver.assert_and_track(
        Implies(And(is_full_refund, Not(verified_defective)), item_in_original_packaging),
        "nl#2_nl