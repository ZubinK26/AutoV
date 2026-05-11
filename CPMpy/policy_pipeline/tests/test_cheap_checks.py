"""Cheap checks (non-triviality + fixtures)."""

from __future__ import annotations

import sys
from pathlib import Path

import cpmpy as cp
import pytest

from cpmpy_wfm_policy.pipeline.cheap_checks import CheapCheckError, run_scalar_cheap_checks


def _root():
    r = Path(__file__).resolve().parents[1]
    if str(r) not in sys.path:
        sys.path.insert(0, str(r))
    return r


def test_nontrivial_rejects_tautology():
    _root()
    from domains.refund_example.signature import customer_kyc_status

    expr = customer_kyc_status == customer_kyc_status
    with pytest.raises(CheapCheckError, match="tautology"):
        run_scalar_cheap_checks(expr, fixtures=None, run_nontrivial=True)


def test_nontrivial_rejects_unsat_rule():
    expr = cp.intvar(0, 1, name="z") < 0
    with pytest.raises(CheapCheckError, match="unsatisfiable"):
        run_scalar_cheap_checks(expr, fixtures=None, run_nontrivial=True)


def test_golden_rules_pass_fixtures():
    _root()
    from domains.refund_example import handwritten_rules as hr
    from domains.refund_example.fixtures import per_rule as pr

    for rid, expr in hr.all_rules().items():
        run_scalar_cheap_checks(expr, fixtures=pr.PER_RULE_FIXTURES[rid], run_nontrivial=True)


def test_slots_alldiff_global_cheap_checks():
    _root()
    from domains.slots_alldiff import handwritten_rules as hr
    from domains.slots_alldiff.fixtures import per_rule as pr

    from cpmpy_wfm_policy.pipeline.cheap_checks import run_global_cheap_checks

    run_global_cheap_checks(
        hr.rule_1,
        global_constraints=[],
        fixtures=pr.PER_RULE_FIXTURES["rule_1"],
        run_nontrivial=True,
    )
