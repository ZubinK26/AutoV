import cpmpy as cp

# Section 2 — Enumerations
KYC_STATUS = {"VERIFIED": 0, "FAILED": 1}
REFUND_TYPE = {"MERCHANT_REFUND": 0, "GOODWILL_CREDIT": 1}
TRANSACTION_STATUS = {"POSTED": 0, "PENDING": 1}

# Section 3 — Entity field declarations (scalar)
customer_kyc_status = cp.intvar(0, 1, name="customer_kyc_status")
customer_vulnerable_flag = cp.boolvar(name="customer_vulnerable_flag")
customer_recent_goodwill_total = cp.intvar(0, 1_000_000, name="customer_recent_goodwill_total")
account_has_sanctions_block = cp.boolvar(name="account_has_sanctions_block")
transaction_amount_pence = cp.intvar(0, 10_000_000, name="transaction_amount_pence")
transaction_status = cp.intvar(0, 1, name="transaction_status")

# Section 5 — Tool-call parameter declarations
refund_call_amount_pence = cp.intvar(0, 10_000_000, name="refund_call_amount_pence")
refund_call_type = cp.intvar(0, 1, name="refund_call_type")

# Section 6 — Derived helpers
customer_kyc_failed = customer_kyc_status == KYC_STATUS["FAILED"]
transaction_is_posted = transaction_status == TRANSACTION_STATUS["POSTED"]
refund_is_merchant = refund_call_type == REFUND_TYPE["MERCHANT_REFUND"]
refund_is_goodwill = refund_call_type == REFUND_TYPE["GOODWILL_CREDIT"]

# Section 8 — Tool-to-state-dependency manifest
TOOL_DEPENDENCIES = {
    "apply_refund": [
        "customer_kyc_status",
        "customer_vulnerable_flag",
        "customer_recent_goodwill_total",
        "account_has_sanctions_block",
        "transaction_amount_pence",
        "transaction_status",
        "refund_call_amount_pence",
        "refund_call_type",
    ],
}
