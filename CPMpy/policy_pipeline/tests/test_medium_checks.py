"""Medium verification: cumulative SAT, mutation smoke."""

from __future__ import annotations

import cpmpy as cp
import pytest

from cpmpy_wfm_policy.verification.medium_checks import (
    MediumCheckError,
    run_cumulative_model_sat,
    run_mutation_flip_dependency_smoke,
)


def test_cumulative_sat_compatible_rules():
    x = cp.boolvar(name="b")
    run_cumulative_model_sat([x == 1, x == 1], global_constraints=None)


def test_cumulative_sat_unsat_raises():
    x = cp.boolvar(name="b")
    with pytest.raises(MediumCheckError, match="UNSAT"):
        run_cumulative_model_sat([x, ~x], global_constraints=None)


def test_mutation_flip_smoke_ok():
    x = cp.boolvar(name="flag")
    expr = x == 1
    run_mutation_flip_dependency_smoke(
        expr, state_when_true={"flag": 1}, critical_field="flag", alternative_value=0
    )
