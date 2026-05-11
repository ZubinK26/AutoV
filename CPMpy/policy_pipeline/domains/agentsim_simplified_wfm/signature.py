import cpmpy as cp

# Section 2 — Enumerations
TRANSACTION_STATUS = {"POSTED": 0, "PENDING": 1}
KYC_STATUS = {"VERIFIED": 0, "FAILED": 1}
REFUND_TYPE = {"MERCHANT_REFUND": 0, "GOODWILL_CREDIT": 1}

# Section 3 — Entity field declarations (scalar)
customer_exists = cp.boolvar(name="customer_exists")
account_exists = cp.boolvar(name="account_exists")
transaction_exists = cp.boolvar(name="transaction_exists")
transaction_status = cp.intvar(0, 1, name="transaction_status")
customer_kyc_status = cp.intvar(0, 1, name="customer_kyc_status")
account_sanctions_block_flag = cp.boolvar(name="account_sanctions_block_flag")
transaction_amount_pence = cp.intvar(0, 10000000, name="transaction_amount_pence")
customer_recent_goodwill_credit_total = cp.intvar(0, 10000000, name="customer_recent_goodwill_credit_total")
customer_vulnerable_flag = cp.boolvar(name="customer_vulnerable_flag")

# Section 4 — Entity field declarations (vector)
# (Empty)

# Section 5 — Tool-call parameter declarations
apply_refund_call_amount_pence = cp.intvar(0, 10000000, name="apply_refund_call_amount_pence")
apply_refund_call_refund_type = cp.intvar(0, 1, name="apply_refund_call_refund_type")

# Section 6 — Derived helpers
# (Empty)

# Section 7 — Domain dimensions
# (Empty)

# Section 8 — Tool-to-state-dependency manifest
TOOL_DEPENDENCIES = {
    "apply_refund": [
        "customer_exists",
        "account_exists",
        "transaction_exists",
        "transaction_status",
        "customer_kyc_status",
        "account_sanctions_block_flag",
        "transaction_amount_pence",
        "customer_recent_goodwill_credit_total",
        "customer_vulnerable_flag",
        "apply_refund_call_amount_pence",
        "apply_refund_call_refund_type"
    ]
}
