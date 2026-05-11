"""Per-rule (state, expected_bool) fixtures for cheap-check direct evaluation."""

from __future__ import annotations

# Canonical full state for refund_example signature (all variable names).
def base_state() -> dict[str, int | bool]:
    return {
        "customer_kyc_status": 0,
        "customer_vulnerable_flag": False,
        "customer_recent_goodwill_total": 0,
        "account_has_sanctions_block": False,
        "transaction_amount_pence": 5000,
        "transaction_status": 0,
        "refund_call_amount_pence": 1000,
        "refund_call_type": 0,
    }


# rule_k matches formalizer index k: NL line k in rules.txt (1-based).
PER_RULE_FIXTURES: dict[str, list[tuple[dict[str, int | bool], bool]]] = {
    "rule_1": [
        (base_state(), True),
        ({**base_state(), "transaction_status": 1}, False),
    ],
    "rule_2": [
        (base_state(), True),
        ({**base_state(), "customer_kyc_status": 1}, False),
    ],
    "rule_3": [
        ({**base_state(), "account_has_sanctions_block": False}, True),
        ({**base_state(), "account_has_sanctions_block": True}, False),
    ],
    "rule_4": [
        (
            {
                **base_state(),
                "refund_call_type": 0,
                "refund_call_amount_pence": 4000,
                "transaction_amount_pence": 5000,
            },
            True,
        ),
        (
            {
                **base_state(),
                "refund_call_type": 0,
                "refund_call_amount_pence": 6000,
                "transaction_amount_pence": 5000,
            },
            False,
        ),
    ],
    "rule_5": [
        (
            {**base_state(), "refund_call_type": 1, "refund_call_amount_pence": 10000},
            True,
        ),
        (
            {**base_state(), "refund_call_type": 1, "refund_call_amount_pence": 10001},
            False,
        ),
    ],
    "rule_6": [
        (
            {
                **base_state(),
                "refund_call_type": 1,
                "customer_recent_goodwill_total": 49000,
                "refund_call_amount_pence": 1000,
            },
            True,
        ),
        (
            {
                **base_state(),
                "refund_call_type": 1,
                "customer_recent_goodwill_total": 49500,
                "refund_call_amount_pence": 501,
            },
            False,
        ),
    ],
    "rule_7": [
        (
            {
                **base_state(),
                "customer_vulnerable_flag": True,
                "refund_call_amount_pence": 20000,
            },
            True,
        ),
        (
            {
                **base_state(),
                "customer_vulnerable_flag": True,
                "refund_call_amount_pence": 20001,
            },
            False,
        ),
    ],
}
