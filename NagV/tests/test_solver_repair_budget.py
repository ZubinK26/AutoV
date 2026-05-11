"""Tests for ``SolverRepairBudget`` and Z3 feasibility helper."""

from __future__ import annotations

import unittest

from nagv.pipeline import SolverRepairBudget
from nagv.z3_runner import Z3Result, z3_feasibility_passed


class TestZ3FeasibilityPassed(unittest.TestCase):
    def test_sat_status(self) -> None:
        z = Z3Result(
            ok=False,
            exit_code=0,
            stdout="",
            stderr="",
            kind="feasibility_pass",
            feasibility_ok=True,
            z3_status="sat",
            unsat_core=None,
            payload={"status": "sat"},
            phase="feasibility",
        )
        self.assertTrue(z3_feasibility_passed(z))

    def test_unsat_status(self) -> None:
        z = Z3Result(
            ok=False,
            exit_code=0,
            stdout="",
            stderr="",
            kind="feasibility_pass",
            feasibility_ok=True,
            z3_status="unsat",
            unsat_core=["a"],
            payload=None,
            phase="feasibility",
        )
        self.assertTrue(z3_feasibility_passed(z))

    def test_feasibility_fail(self) -> None:
        z = Z3Result(
            ok=False,
            exit_code=1,
            stdout="",
            stderr="",
            kind="feasibility",
            feasibility_ok=False,
            z3_status=None,
            unsat_core=None,
            payload=None,
            phase="feasibility",
        )
        self.assertFalse(z3_feasibility_passed(z))


class TestSolverRepairBudget(unittest.TestCase):
    def test_phase_b_respects_floor_until_semantic_done(self) -> None:
        b = SolverRepairBudget(cap=10, floor=2)
        self.assertTrue(b.can_repair_phase_b())
        for _ in range(7):
            b.spend(1)
        self.assertTrue(b.can_repair_phase_b())
        b.spend(1)
        self.assertFalse(b.can_repair_phase_b())
        self.assertTrue(b.can_repair_phase_d())

    def test_phase_d_uses_remaining_after_b_blocked(self) -> None:
        b = SolverRepairBudget(cap=10, floor=2)
        for _ in range(8):
            b.spend(1)
        self.assertFalse(b.can_repair_phase_b())
        self.assertTrue(b.can_repair_phase_d())
        b.spend(1)
        self.assertTrue(b.can_repair_phase_d())
        b.spend(1)
        self.assertFalse(b.can_repair_phase_d())

    def test_phase_b_disabled_after_semantic_complete(self) -> None:
        b = SolverRepairBudget(cap=10, floor=2)
        b.mark_semantic_complete()
        self.assertFalse(b.can_repair_phase_b())
        self.assertTrue(b.can_repair_phase_d())


if __name__ == "__main__":
    unittest.main()
