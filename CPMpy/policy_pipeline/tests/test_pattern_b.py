"""Pattern B SAT + unsat core (Z3)."""

from __future__ import annotations

import sys
from pathlib import Path

import cpmpy as cp
import pytest

from cpmpy_wfm_policy.runtime.pattern_b import gate_pattern_b_rules


def _root():
    r = Path(__file__).resolve().parents[1]
    if str(r) not in sys.path:
        sys.path.insert(0, str(r))
    return r


def test_gate_jointly_sat():
    _root()
    x = cp.intvar(0, 1, name="x")
    rules = {"r1": x == 0, "r2": x >= 0}
    ok, viol, _ms = gate_pattern_b_rules(rules, {"x": 0}, [], solver="z3")
    assert ok and viol == []


def test_gate_jointly_unsat_core():
    _root()
    x = cp.intvar(0, 1, name="x")
    rules = {"r1": x == 0, "r2": x == 1}
    ok, viol, _ms = gate_pattern_b_rules(rules, {"x": 0}, [], solver="z3")
    assert not ok
    assert viol  # at least one rule in conflict


def test_gate_requires_z3_solver_name():
    _root()
    x = cp.intvar(0, 1, name="x")
    from cpmpy_wfm_policy.runtime.pattern_b import PatternBError

    with pytest.raises(PatternBError, match="z3"):
        gate_pattern_b_rules({"r1": x == 0}, {"x": 0}, [], solver="ortools")
