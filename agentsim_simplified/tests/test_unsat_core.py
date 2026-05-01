"""Unsat-core expectations for ``decide(..., unsat_core=True)`` (Z3 minimization may omit redundant rules)."""

from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("z3")

from agentsim_simplified.policy_source import default_refined_policy_path
from agentsim_simplified.seed_data import load_db
from agentsim_simplified.simpl_checker import (
    QUERY_ASSUME_IS_PERMITTED,
    QUERY_ASSUME_NOT_PERMITTED,
    SimplPolicyChecker,
    SimplVerdict,
)
from agentsim_simplified.simpl_scenario import RefundCallScenario
from agentsim_simplified.tools import lookup_bundle


@pytest.fixture(scope="module")
def checker() -> SimplPolicyChecker:
    p = default_refined_policy_path()
    if not p.is_file():
        pytest.skip(f"missing refined policy: {p}")
    return SimplPolicyChecker(policy_path=p)


def _deny_core(checker: SimplPolicyChecker, sc: RefundCallScenario) -> frozenset[str]:
    d = checker.decide(sc, unsat_core=True)
    assert d.verdict == SimplVerdict.DENIED
    assert d.unsat_core is not None
    return d.unsat_core


def _permit_core(checker: SimplPolicyChecker, sc: RefundCallScenario) -> frozenset[str]:
    d = checker.decide(sc, unsat_core=True)
    assert d.verdict == SimplVerdict.PERMITTED
    assert d.unsat_core is not None
    return d.unsat_core


def test_unsat_deny_missing_customer_names_rule_and_query(checker: SimplPolicyChecker) -> None:
    b = lookup_bundle(load_db(), "T-001")
    sc = replace(
        RefundCallScenario.from_bundle(b, refund_type="MERCHANT_REFUND", refund_amount_pence=1000),
        customer_exists_in_db=False,
    )
    core = _deny_core(checker, sc)
    assert "rule_customer_must_exist_in_db" in core
    assert QUERY_ASSUME_IS_PERMITTED in core


def test_unsat_deny_missing_transaction_names_rule_and_query(checker: SimplPolicyChecker) -> None:
    b = lookup_bundle(load_db(), "T-001")
    sc = replace(
        RefundCallScenario.from_bundle(b, refund_type="MERCHANT_REFUND", refund_amount_pence=1000),
        transaction_exists_in_db=False,
    )
    core = _deny_core(checker, sc)
    assert "rule_transaction_must_exist_in_db" in core
    assert QUERY_ASSUME_IS_PERMITTED in core


def test_unsat_deny_failed_kyc_in_core(checker: SimplPolicyChecker) -> None:
    sc = RefundCallScenario.from_bundle(
        lookup_bundle(load_db(), "T-004"),
        refund_type="MERCHANT_REFUND",
        refund_amount_pence=2000,
    )
    core = _deny_core(checker, sc)
    assert "rule_failed_kyc" in core
    assert QUERY_ASSUME_IS_PERMITTED in core


def test_unsat_deny_pending_merchant_names_posted_rule(checker: SimplPolicyChecker) -> None:
    sc = RefundCallScenario.from_bundle(
        lookup_bundle(load_db(), "T-007"),
        refund_type="MERCHANT_REFUND",
        refund_amount_pence=500,
    )
    core = _deny_core(checker, sc)
    assert "rule_transaction_must_be_posted" in core


def test_unsat_deny_goodwill_12000_types_rule_not_merchant_exceeds(checker: SimplPolicyChecker) -> None:
    sc = RefundCallScenario.from_bundle(
        lookup_bundle(load_db(), "T-001"),
        refund_type="GOODWILL_CREDIT",
        refund_amount_pence=12000,
    )
    core = _deny_core(checker, sc)
    assert "rule_goodwill_credit_exceeds_cap" in core
    assert "rule_merchant_amount_exceeds_original" not in core


def test_unsat_deny_merchant_5001_names_merchant_rule_not_goodwill_cap(checker: SimplPolicyChecker) -> None:
    sc = RefundCallScenario.from_bundle(
        lookup_bundle(load_db(), "T-001"),
        refund_type="MERCHANT_REFUND",
        refund_amount_pence=5001,
    )
    core = _deny_core(checker, sc)
    assert "rule_merchant_amount_exceeds_original" in core
    assert "rule_goodwill_credit_exceeds_cap" not in core


def test_unsat_deny_failed_kyc_and_vulnerable_at_least_failed_kyc(checker: SimplPolicyChecker) -> None:
    """Tests-NL #17: core may include only ``rule_failed_kyc`` if Z3 finds it sufficient (doc allows)."""
    sc = RefundCallScenario(
        customer_exists_in_db=True,
        account_exists_in_db=True,
        transaction_exists_in_db=True,
        customer_kyc="FAILED",
        customer_vulnerable=True,
        customer_recent_goodwill_pence=0,
        account_has_sanctions_block=False,
        transaction_amount_pence=30000,
        transaction_status="POSTED",
        refund_type="MERCHANT_REFUND",
        refund_amount_pence=25000,
    )
    core = _deny_core(checker, sc)
    assert "rule_failed_kyc" in core
    # If minimizer keeps both blocking paths, vulnerable cap may appear too:
    # assert "rule_vulnerable_customer_refund_cap" in core  # optional


def test_unsat_permit_baseline_includes_completion_and_neg_query(checker: SimplPolicyChecker) -> None:
    sc = RefundCallScenario.from_bundle(
        lookup_bundle(load_db(), "T-001"),
        refund_type="MERCHANT_REFUND",
        refund_amount_pence=3000,
    )
    core = _permit_core(checker, sc)
    assert QUERY_ASSUME_NOT_PERMITTED in core
    assert "rule_positive_completion" in core
