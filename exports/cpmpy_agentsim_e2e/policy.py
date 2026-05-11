"""Generated policy module (cpmpy_wfm_policy orchestrator)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_RULE_MODULES = json.loads("[\"import cpmpy as cp\\nrule_1 = customer_exists\\n\", \"import cpmpy as cp\\nrule_2 = account_exists\\n\", \"import cpmpy as cp\\nrule_3 = transaction_exists\\n\", \"import cpmpy as cp\\nrule_4 = transaction_status == TRANSACTION_STATUS[\\\"POSTED\\\"]\\n\", \"import cpmpy as cp\\nrule_5 = customer_kyc_status != KYC_STATUS['FAILED']\\n\", \"import cpmpy as cp\\nrule_6 = ~account_sanctions_block_flag\\n\", \"import cpmpy as cp\\nrule_7 = (apply_refund_call_refund_type == REFUND_TYPE['MERCHANT_REFUND']).implies(apply_refund_call_amount_pence <= transaction_amount_pence)\\n\", \"import cpmpy as cp\\nrule_8 = (apply_refund_call_refund_type == REFUND_TYPE['GOODWILL_CREDIT']).implies(apply_refund_call_amount_pence <= 10000)\\n\", \"import cpmpy as cp\\nrule_9 = (apply_refund_call_refund_type == REFUND_TYPE['GOODWILL_CREDIT']).implies((customer_recent_goodwill_credit_total + apply_refund_call_amount_pence) <= 50000)\\n\", \"import cpmpy as cp\\nrule_10 = ~(customer_vulnerable_flag & (apply_refund_call_amount_pence > 20000))\\n\"]")

_dir = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("domain_signature", _dir / "signature.py")
if _spec is None or _spec.loader is None:
    raise ImportError("cannot load signature.py")
_sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sig)
_ns = {k: v for k, v in vars(_sig).items() if not k.startswith('_')}
for i, _src in enumerate(_RULE_MODULES, start=1):
    exec(compile(_src, f"<rule_{i}>", "exec"), _ns, _ns)

rule_1 = _ns['rule_1']
rule_2 = _ns['rule_2']
rule_3 = _ns['rule_3']
rule_4 = _ns['rule_4']
rule_5 = _ns['rule_5']
rule_6 = _ns['rule_6']
rule_7 = _ns['rule_7']
rule_8 = _ns['rule_8']
rule_9 = _ns['rule_9']
rule_10 = _ns['rule_10']


def all_rules() -> dict[str, object]:
    return {
        "rule_1": rule_1,
        "rule_2": rule_2,
        "rule_3": rule_3,
        "rule_4": rule_4,
        "rule_5": rule_5,
        "rule_6": rule_6,
        "rule_7": rule_7,
        "rule_8": rule_8,
        "rule_9": rule_9,
        "rule_10": rule_10,
    }
