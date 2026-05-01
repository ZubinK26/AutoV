"""
Regression checks for scenarios described in ``agentsim/Tests-NL-Queries.md``.

The markdown suite was written for a validator that returns ALLOW/BLOCK plus **named unsat cores**.
:class:`GuardrailsPolicyChecker` only reports ``permitted`` / ``denied`` / ``ambiguous``, and treats
**policy+scenario UNSAT** (contradictory world facts) as ``ambiguous`` with a UNSAT detail string—not
the same as ``denied`` (entailed ``not is-permitted``).

See module docstring in the first revision for the MD-vs-model gap analysis.
"""

from __future__ import annotations

import pytest

pytest.importorskip("z3")

from agentsim.runtime.guardrails_checker import (
    GuardrailsPolicyChecker,
    GuardrailsVerdict,
    default_guardrails_policy_path,
)
from agentsim.runtime.guardrails_scenario import GuardrailsScenario


def _unsat_grounding(detail: str) -> bool:
    return "UNSAT" in detail


@pytest.fixture(scope="module")
def checker() -> GuardrailsPolicyChecker:
    path = default_guardrails_policy_path()
    if not path.is_file():
        pytest.skip(f"refined policy missing: {path}")
    return GuardrailsPolicyChecker(policy_path=path)


@pytest.mark.parametrize(
    "name,scenario",
    [
        (
            "1a goodwill 10000",
            GuardrailsScenario(
                primary_tool="apply_goodwill_credit",
                refund_amount_pence=10_000,
                human_approval_granted=False,
            ),
        ),
        (
            "2a rolling window under cap",
            GuardrailsScenario(
                primary_tool="apply_goodwill_credit",
                recent_goodwill_credit_total=49_500,
                refund_amount_pence=400,
            ),
        ),
    ],
)
def test_nl_md_allow_paths_not_denied(checker: GuardrailsPolicyChecker, name: str, scenario: GuardrailsScenario):
    """MD expects ALLOW; model often leaves ``is-permitted`` under-specified → ``ambiguous``, not ``permitted``."""

    d = checker.decide(scenario)
    assert d.verdict != GuardrailsVerdict.DENIED, f"{name}: unexpected DENIED ({d.detail})"
    assert not _unsat_grounding(d.detail), f"{name}: unexpected inconsistent scenario ({d.detail})"


def test_nl_md_1b_goodwill_10001_blocked_without_approval(checker: GuardrailsPolicyChecker):
    d = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_goodwill_credit",
            refund_amount_pence=10_001,
            human_approval_granted=False,
        )
    )
    assert d.verdict == GuardrailsVerdict.DENIED


def test_nl_md_2b_goodwill_over_accumulator_blocked(checker: GuardrailsPolicyChecker):
    d = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_goodwill_credit",
            recent_goodwill_credit_total=50_100,
            refund_amount_pence=400,
        )
    )
    assert d.verdict == GuardrailsVerdict.DENIED


def test_nl_md_3_sanctions_block_dispute_refund(checker: GuardrailsPolicyChecker):
    d = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_refund",
            refund_type="DISPUTE_REFUND",
            refund_amount_pence=2500,
            extra_asserts=[
                "(assert (exists ((r Restriction)) (and (= (restriction-account r) sim_a) (= (is-active-restriction r) true) (= (restriction-type r) sanctions-block))))",
                "(assert (exists ((d Dispute)) (and (= (dispute-transaction d) sim_t) (= (dispute-status d) dispute-approved))))",
            ],
        )
    )
    assert d.verdict == GuardrailsVerdict.DENIED


def test_nl_md_4_vulnerable_refund_cda(checker: GuardrailsPolicyChecker):
    d0 = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_refund",
            refund_type="MERCHANT_REFUND",
            refund_amount_pence=3000,
            customer_vulnerable=True,
        )
    )
    assert d0.verdict != GuardrailsVerdict.PERMITTED, "without fair-value CDA check, should not entail ALLOW"
    # MD: BLOCK; checker often yields ambiguous (no full definition of is-permitted).
    assert d0.verdict in (GuardrailsVerdict.DENIED, GuardrailsVerdict.AMBIGUOUS)

    d1 = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_refund",
            refund_type="MERCHANT_REFUND",
            refund_amount_pence=3000,
            customer_vulnerable=True,
            extra_asserts=[
                "(declare-const sim_cda ConsumerDutyAssessment)",
                "(assert (= (assessment-interaction sim_cda) current-interaction))",
                "(assert (= (fair-value-check-passed sim_cda) true))",
                "(assert (= (clear-communication-check-passed sim_cda) true))",
            ],
        )
    )
    assert d1.verdict != GuardrailsVerdict.DENIED
    assert not _unsat_grounding(d1.detail)
    # MD expects ALLOW; ``is-permitted`` is often not fully entailed → ``ambiguous`` is acceptable.
    assert d1.verdict in (GuardrailsVerdict.PERMITTED, GuardrailsVerdict.AMBIGUOUS)


def test_nl_md_5_unauthorized_window_119_ok_121_inconsistent(checker: GuardrailsPolicyChecker):
    d_ok = checker.decide(
        GuardrailsScenario(
            primary_tool="initiate_dispute",
            dispute_type="UNAUTHORIZED",
            days_since_posted=119,
        )
    )
    assert d_ok.verdict != GuardrailsVerdict.DENIED
    assert not _unsat_grounding(d_ok.detail)

    d_bad = checker.decide(
        GuardrailsScenario(
            primary_tool="initiate_dispute",
            dispute_type="UNAUTHORIZED",
            days_since_posted=121,
        )
    )
    # MD: BLOCK via UNSAT core; here facts contradict policy axioms → UNSAT, not DENIED.
    assert d_bad.verdict == GuardrailsVerdict.AMBIGUOUS
    assert _unsat_grounding(d_bad.detail)


@pytest.mark.parametrize(
    "amount,expect_sat_grounding",
    [
        (9999, False),
        (10_000, True),
        (30_000_000, True),
        (30_000_001, False),
    ],
)
def test_nl_md_6_section75_amount_grounding(
    checker: GuardrailsPolicyChecker, amount: int, expect_sat_grounding: bool
):
    d = checker.decide(
        GuardrailsScenario(
            primary_tool="initiate_dispute",
            dispute_type="SECTION_75",
            transaction_amount_pence=amount,
            transaction_is_debit=True,
            days_since_posted=30,
        )
    )
    if expect_sat_grounding:
        assert not _unsat_grounding(d.detail), f"amount={amount}: expected SAT scenario"
        assert d.verdict != GuardrailsVerdict.DENIED
    else:
        assert _unsat_grounding(d.detail), f"amount={amount}: expected UNSAT (violates section-75 bounds axiom)"


def test_nl_md_7_frozen_refund_inconsistent_with_modifies_financial_axiom(checker: GuardrailsPolicyChecker):
    """MD piles FROZEN + MERCHANT_REFUND; r_f8b74 forces ACTIVE|RESTRICTED for financial writes → UNSAT."""

    d = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_refund",
            refund_type="MERCHANT_REFUND",
            refund_amount_pence=500,
            customer_kyc="FAILED",
            customer_sanctions=True,
            account_status="FROZEN",
        )
    )
    assert d.verdict == GuardrailsVerdict.AMBIGUOUS
    assert _unsat_grounding(d.detail)


@pytest.mark.parametrize("human_lift", [True, False])
def test_nl_md_8_court_order_lift_blocked(checker: GuardrailsPolicyChecker, human_lift: bool):
    d = checker.decide(
        GuardrailsScenario(
            primary_tool="lift_account_restriction",
            lift_restriction_type="COURT_ORDER",
            restriction_human_action_required=human_lift,
            human_approval_granted=True,
        )
    )
    assert d.verdict == GuardrailsVerdict.DENIED


def test_nl_md_9_fraud_confirmed_blocks(checker: GuardrailsPolicyChecker):
    fraud_extras = [
        "(declare-const sim_fr FraudReport)",
        "(assert (= (fraud-report-status sim_fr) fraud-confirmed))",
        "(assert (fraud-report-references-transaction sim_fr sim_t))",
    ]
    d_a = checker.decide(
        GuardrailsScenario(
            primary_tool="initiate_dispute",
            dispute_type="UNAUTHORIZED",
            extra_asserts=list(fraud_extras),
        )
    )
    assert d_a.verdict == GuardrailsVerdict.DENIED

    d_b = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_refund",
            refund_type="DISPUTE_REFUND",
            refund_amount_pence=1500,
            extra_asserts=[
                *fraud_extras,
                "(assert (exists ((d Dispute)) (and (= (dispute-transaction d) sim_t) (= (dispute-status d) dispute-approved))))",
            ],
        )
    )
    assert d_b.verdict == GuardrailsVerdict.DENIED


def test_nl_md_10_clean_refund_not_denied(checker: GuardrailsPolicyChecker):
    d = checker.decide(
        GuardrailsScenario(
            primary_tool="apply_refund",
            refund_type="MERCHANT_REFUND",
            refund_amount_pence=5000,
            transaction_amount_pence=5000,
            transaction_is_debit=True,
            customer_kyc="VERIFIED",
            customer_vulnerable=False,
            customer_sanctions=False,
            recent_goodwill_credit_total=0,
            recent_dispute_count=0,
            account_status="ACTIVE",
        )
    )
    assert d.verdict != GuardrailsVerdict.DENIED
    assert not _unsat_grounding(d.detail)
