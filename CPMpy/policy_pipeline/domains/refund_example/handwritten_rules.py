"""
Reference scalar rules for refund_example (same intent as rules.txt).
Used by tests and as a sanity target for the formalizer.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_dir = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("refund_example_signature", _dir / "signature.py")
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load signature.py")
_sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sig)

rule_1 = _sig.transaction_is_posted
rule_2 = ~_sig.customer_kyc_failed
rule_3 = ~_sig.account_has_sanctions_block
rule_4 = ~(_sig.refund_is_merchant & (_sig.refund_call_amount_pence > _sig.transaction_amount_pence))
rule_5 = ~(_sig.refund_is_goodwill & (_sig.refund_call_amount_pence > 10000))
rule_6 = ~(
    _sig.refund_is_goodwill
    & (
        (_sig.customer_recent_goodwill_total + _sig.refund_call_amount_pence) > 50000
    )
)
rule_7 = ~(_sig.customer_vulnerable_flag & (_sig.refund_call_amount_pence > 20000))


def all_rules() -> dict[str, object]:
    return {
        "rule_1": rule_1,
        "rule_2": rule_2,
        "rule_3": rule_3,
        "rule_4": rule_4,
        "rule_5": rule_5,
        "rule_6": rule_6,
        "rule_7": rule_7,
    }
