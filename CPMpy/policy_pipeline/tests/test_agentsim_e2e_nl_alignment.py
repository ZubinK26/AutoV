"""
NL-aligned scenario tests for exports/cpmpy_agentsim_e2e (agentsim_simplified_wfm rules).

Skipped if the bundle is missing — copy or regenerate the export under repo-root exports/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cpmpy_wfm_policy.runtime.pattern_a import gate_scalar_rules

# Repo layout: CPMpy/policy_pipeline/tests/this_file -> parents[3] = AutoV workspace root
_WORKSPACE = Path(__file__).resolve().parents[3]
_BUNDLE = _WORKSPACE / "exports" / "cpmpy_agentsim_e2e"


def _load_policy():
    if not (_BUNDLE / "policy.py").is_file():
        pytest.skip(f"missing policy bundle: {_BUNDLE}")
    import importlib.util

    spec = importlib.util.spec_from_file_location("agentsim_e2e_policy", _BUNDLE / "policy.py")
    if spec is None or spec.loader is None:
        pytest.skip("cannot load policy")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.all_rules()


# REFUND_TYPE / KYC / TRANSACTION encoding must match signature.py in bundle
RT_MERCHANT = 0
RT_GOODWILL = 1
KYC_VERIFIED = 0
KYC_FAILED = 1
TX_POSTED = 0
TX_PENDING = 1


def _base_state(**overrides: bool | int) -> dict[str, int | bool]:
    st: dict[str, int | bool] = {
        "customer_exists": True,
        "account_exists": True,
        "transaction_exists": True,
        "transaction_status": TX_POSTED,
        "customer_kyc_status": KYC_VERIFIED,
        "account_sanctions_block_flag": False,
        "transaction_amount_pence": 5000,
        "customer_recent_goodwill_credit_total": 0,
        "customer_vulnerable_flag": False,
        "apply_refund_call_amount_pence": 1000,
        "apply_refund_call_refund_type": RT_MERCHANT,
    }
    st.update(overrides)
    return st


@pytest.fixture(scope="module")
def rules():
    return _load_policy()


def test_baseline_all_rules_hold(rules):
    ok, violated, _ = gate_scalar_rules(rules, _base_state())
    assert ok, violated


def test_rule1_customer_must_exist(rules):
    ok, violated, _ = gate_scalar_rules(rules, _base_state(customer_exists=False))
    assert not ok
    assert "rule_1" in violated


def test_rule4_pending_transaction_blocks(rules):
    ok, violated, _ = gate_scalar_rules(rules, _base_state(transaction_status=TX_PENDING))
    assert not ok
    assert "rule_4" in violated


def test_rule5_failed_kyc_blocks(rules):
    ok, violated, _ = gate_scalar_rules(rules, _base_state(customer_kyc_status=KYC_FAILED))
    assert not ok
    assert "rule_5" in violated


def test_rule6_sanctions_block(rules):
    ok, violated, _ = gate_scalar_rules(rules, _base_state(account_sanctions_block_flag=True))
    assert not ok
    assert "rule_6" in violated


def test_rule7_merchant_amount_boundary(rules):
    ok, _, _ = gate_scalar_rules(
        rules,
        _base_state(
            apply_refund_call_refund_type=RT_MERCHANT,
            transaction_amount_pence=5000,
            apply_refund_call_amount_pence=5000,
        ),
    )
    assert ok
    ok2, viol, _ = gate_scalar_rules(
        rules,
        _base_state(
            apply_refund_call_refund_type=RT_MERCHANT,
            transaction_amount_pence=5000,
            apply_refund_call_amount_pence=5001,
        ),
    )
    assert not ok2
    assert "rule_7" in viol


def test_rule8_goodwill_ten_thousand_boundary(rules):
    ok, _, _ = gate_scalar_rules(
        rules,
        _base_state(
            apply_refund_call_refund_type=RT_GOODWILL,
            apply_refund_call_amount_pence=10000,
        ),
    )
    assert ok
    ok2, viol, _ = gate_scalar_rules(
        rules,
        _base_state(
            apply_refund_call_refund_type=RT_GOODWILL,
            apply_refund_call_amount_pence=10001,
        ),
    )
    assert not ok2
    assert "rule_8" in viol


def test_rule9_goodwill_rolling_fifty_thousand_boundary(rules):
    ok, _, _ = gate_scalar_rules(
        rules,
        _base_state(
            apply_refund_call_refund_type=RT_GOODWILL,
            customer_recent_goodwill_credit_total=49000,
            apply_refund_call_amount_pence=1000,
        ),
    )
    assert ok
    ok2, viol, _ = gate_scalar_rules(
        rules,
        _base_state(
            apply_refund_call_refund_type=RT_GOODWILL,
            customer_recent_goodwill_credit_total=49500,
            apply_refund_call_amount_pence=501,
        ),
    )
    assert not ok2
    assert "rule_9" in viol


def test_rule10_vulnerable_twenty_thousand_boundary(rules):
    # transaction_amount must cover refund so rule_7 does not mask rule_10
    ok, _, _ = gate_scalar_rules(
        rules,
        _base_state(
            customer_vulnerable_flag=True,
            transaction_amount_pence=50_000,
            apply_refund_call_refund_type=RT_MERCHANT,
            apply_refund_call_amount_pence=20000,
        ),
    )
    assert ok
    ok2, viol, _ = gate_scalar_rules(
        rules,
        _base_state(
            customer_vulnerable_flag=True,
            transaction_amount_pence=50_000,
            apply_refund_call_refund_type=RT_MERCHANT,
            apply_refund_call_amount_pence=20001,
        ),
    )
    assert not ok2
    assert "rule_10" in viol


def test_rule2_rule3_existence_account_transaction(rules):
    ok, viol, _ = gate_scalar_rules(rules, _base_state(account_exists=False))
    assert not ok
    assert "rule_2" in viol
    ok2, viol2, _ = gate_scalar_rules(rules, _base_state(transaction_exists=False))
    assert not ok2
    assert "rule_3" in viol2
