"""
Parameterized tests mirroring ``agentsim_simplified/Tests-NL.md``.

Unsat-core wording in the doc is not asserted (checker does not map Z3 cores to rule IDs).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("z3")

from agentsim_simplified.policy_source import default_refined_policy_path
from agentsim_simplified.seed_data import load_db
from agentsim_simplified.simpl_checker import SimplPolicyChecker, SimplVerdict
from agentsim_simplified.simpl_scenario import RefundCallScenario
from agentsim_simplified.tools import lookup_bundle


def _check(checker: SimplPolicyChecker, sc: RefundCallScenario, expect_allow: bool) -> None:
    d = checker.decide(sc)
    if expect_allow:
        assert d.verdict == SimplVerdict.PERMITTED, (d.verdict, d.detail)
    else:
        assert d.verdict == SimplVerdict.DENIED, (d.verdict, d.detail)


@pytest.fixture(scope="module")
def checker() -> SimplPolicyChecker:
    p = default_refined_policy_path()
    if not p.is_file():
        pytest.skip(f"missing refined policy: {p}")
    return SimplPolicyChecker(policy_path=p)


@pytest.fixture(scope="module")
def db():
    return load_db()


@pytest.mark.parametrize(
    ("name", "build", "expect_allow"),
    [
        (
            "1 clean baseline T-001 MERCHANT 3000",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-001"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=3000,
            ),
            True,
        ),
        (
            "2 missing customer R-1",
            lambda _db: RefundCallScenario.from_bundle(
                None,
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=1000,
            ),
            False,
        ),
        (
            "3 missing transaction R-3",
            lambda db: replace(
                RefundCallScenario.from_bundle(
                    lookup_bundle(db, "T-001"),
                    refund_type="MERCHANT_REFUND",
                    refund_amount_pence=1000,
                ),
                transaction_exists_in_db=False,
            ),
            False,
        ),
        (
            "4 T-007 PENDING MERCHANT blocks R-4",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-007"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=500,
            ),
            False,
        ),
        (
            "5 T-004 FAILED KYC MERCHANT R-5",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-004"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=2000,
            ),
            False,
        ),
        (
            "6 T-004 VERIFIED KYC ALLOW pair to 5",
            lambda db: replace(
                RefundCallScenario.from_bundle(
                    lookup_bundle(db, "T-004"),
                    refund_type="MERCHANT_REFUND",
                    refund_amount_pence=2000,
                ),
                customer_kyc="VERIFIED",
            ),
            True,
        ),
        (
            "7 T-005 sanctions MERCHANT R-6",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-005"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=3000,
            ),
            False,
        ),
        (
            "8 T-005 no sanctions ALLOW pair to 7",
            lambda db: replace(
                RefundCallScenario.from_bundle(
                    lookup_bundle(db, "T-005"),
                    refund_type="MERCHANT_REFUND",
                    refund_amount_pence=3000,
                ),
                account_has_sanctions_block=False,
            ),
            True,
        ),
        (
            "9 T-001 MERCHANT full 5000 R-7 strict",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-001"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=5000,
            ),
            True,
        ),
        (
            "10 T-001 MERCHANT 5001 blocks R-7",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-001"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=5001,
            ),
            False,
        ),
        (
            "11 T-001 GOODWILL 10000 R-8 strict",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-001"),
                refund_type="GOODWILL_CREDIT",
                refund_amount_pence=10000,
            ),
            True,
        ),
        (
            "12 T-001 GOODWILL 10001 blocks R-8",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-001"),
                refund_type="GOODWILL_CREDIT",
                refund_amount_pence=10001,
            ),
            False,
        ),
        (
            "13 rolling window 49000+1000 = 50000 ALLOW R-9 strict",
            lambda db: replace(
                RefundCallScenario.from_bundle(
                    lookup_bundle(db, "T-001"),
                    refund_type="GOODWILL_CREDIT",
                    refund_amount_pence=1000,
                ),
                customer_recent_goodwill_pence=49000,
            ),
            True,
        ),
        (
            "14 C-003 49500 + 501 GOODWILL blocks R-9",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-003"),
                refund_type="GOODWILL_CREDIT",
                refund_amount_pence=501,
            ),
            False,
        ),
        (
            "15 C-002 T-002 MERCHANT 20000 vulnerable ALLOW R-10 strict",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-002"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=20000,
            ),
            True,
        ),
        (
            "16 C-002 T-002 MERCHANT 20001 vulnerable blocks R-10",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-002"),
                refund_type="MERCHANT_REFUND",
                refund_amount_pence=20001,
            ),
            False,
        ),
        (
            "17 FAILED KYC + vulnerable MERCHANT 25000 BLOCK R-5 R-10",
            lambda _db: RefundCallScenario(
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
            ),
            False,
        ),
        (
            "18 T-001 GOODWILL 12000 blocks R-8 not merchant R-7",
            lambda db: RefundCallScenario.from_bundle(
                lookup_bundle(db, "T-001"),
                refund_type="GOODWILL_CREDIT",
                refund_amount_pence=12000,
            ),
            False,
        ),
    ],
)
def test_tests_nl_matrix(name: str, build, expect_allow: bool, checker: SimplPolicyChecker, db) -> None:
    sc = build(db)
    _check(checker, sc, expect_allow)
