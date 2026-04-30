from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentsim.runtime.models import Decision, ToolCall


class Z3LegalityChecker:
    """
    Loads bundled SMT-LIB (goodwill cap rule), checks per agentsim/03:
    ground state + amount, ``(assert (not sim-legal-goodwill))``, UNSAT ⇒ ALLOW.
    """

    RULE_GOODWILL_CAP = "R-VULN-GOODWILL-CAP"

    def __init__(self, policy_smt2_text: str) -> None:
        from z3 import Bool, Int, Not, parse_smt2_string, sat, unsat

        self._Not = Not
        self._sat = sat
        self._unsat = unsat
        assertions = parse_smt2_string(policy_smt2_text)
        self._solver_template = assertions
        self._vuln = Bool("sim-vulnerable")
        self._amt = Int("sim-proposed-goodwill-pence")
        self._legal = Bool("sim-legal-goodwill")

    def validate_call(self, call: ToolCall, state: dict[str, Any]) -> Decision:
        if call.tool_name != "apply_goodwill_credit":
            return Decision(allow=True)

        vulnerable = bool(state.get("customer_vulnerable_flag", False))
        try:
            proposed = int(call.parameters.get("amount_pence", 0))
        except (TypeError, ValueError):
            proposed = 0

        allow, expl = self._check_apply_goodwill(vulnerable, proposed)
        if allow:
            return Decision(allow=True)
        return Decision(
            allow=False,
            unsat_core=[self.RULE_GOODWILL_CAP],
            explanation=expl,
        )

    def _check_apply_goodwill(self, vulnerable: bool, amount_pence: int) -> tuple[bool, str]:
        from z3 import Solver

        slv = Solver()
        for a in self._solver_template:
            slv.add(a)
        slv.push()
        slv.add(self._vuln == vulnerable)
        slv.add(self._amt == amount_pence)
        slv.add(self._Not(self._legal))
        result = slv.check()
        slv.pop()
        if result == self._unsat:
            return True, ""
        if result == self._sat:
            return (
                False,
                "Goodwill credit exceeds £500 for a vulnerable customer (rule "
                + self.RULE_GOODWILL_CAP
                + ").",
            )
        return True, ""


def make_z3_policy_validate(checker: Z3LegalityChecker) -> Callable[[ToolCall, dict[str, Any]], Decision]:
    """``ValidateFn`` for :class:`~agentsim.runtime.write_tools.WriteToolExecutor`."""

    def validate(call: ToolCall, state: dict[str, Any]) -> Decision:
        return checker.validate_call(call, state)

    return validate
