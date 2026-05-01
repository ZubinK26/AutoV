"""Z3 decision procedure: grounded scenario + ``policy_model_refined.smt2`` → permit / deny / ambiguous."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from agentsim.runtime.guardrails_scenario import GuardrailsScenario


def repo_root_from_here() -> Path:
    """``agentsim/runtime/`` → workspace root (AutoV)."""

    return Path(__file__).resolve().parents[2]


def default_guardrails_policy_path() -> Path:
    """Canonical refined guardrails policy (same directory as WFM export)."""

    return (
        repo_root_from_here()
        / "exports"
        / "nl_chunk_smt_runs"
        / "04_agentic_guardrails"
        / "policy_model_refined.smt2"
    )


class GuardrailsVerdict(str, Enum):
    """Whether ``is-permitted(sim_tc)`` is forced, forbidden, or underdetermined."""

    PERMITTED = "permitted"  # G ⇒ is-permitted
    DENIED = "denied"  # G ⇒ ¬is-permitted
    AMBIGUOUS = "ambiguous"  # both consistent with G


class GuardrailsDecision:
    __slots__ = ("verdict", "detail")

    def __init__(self, verdict: GuardrailsVerdict, detail: str = "") -> None:
        self.verdict = verdict
        self.detail = detail

    def permitted(self) -> bool:
        return self.verdict == GuardrailsVerdict.PERMITTED

    def to_dict(self) -> dict:
        return {"verdict": self.verdict.value, "detail": self.detail}


def _find_func_decl(assertions: list, name: str):
    from z3 import is_app, is_quantifier

    seen: dict[tuple[str, int], object] = {}

    def visit2(e) -> None:
        if is_app(e):
            d = e.decl()
            key = (d.name(), d.arity())
            if key[0] == name and key[1] > 0:
                seen[key] = d
            for c in e.children():
                visit2(c)
        elif is_quantifier(e):
            visit2(e.body())

    for a in assertions:
        visit2(a)
    for (_n, _arity), d in seen.items():
        if _n == name:
            return d
    msg = f"no function declaration named {name!r} found in policy"
    raise ValueError(msg)


def _find_const_in_assertions(assertions: list, cname: str):
    from z3 import is_app, is_const, is_quantifier

    found: list = []

    def visit(e) -> None:
        if is_const(e) and e.decl().name() == cname:
            found.append(e)
        elif is_app(e):
            for ch in e.children():
                visit(ch)
        elif is_quantifier(e):
            visit(e.body())

    for a in assertions:
        visit(a)
    if not found:
        msg = f"no constant {cname!r} found in assertions"
        raise ValueError(msg)
    return found[0]


class GuardrailsPolicyChecker:
    """
    Load policy text once (validated at init). Each :meth:`decide` parses **policy + grounding**
    in a **single** ``parse_smt2_string`` so all sorts share one Z3 context (avoids Windows issues
    when re-parsing fragments with a foreign context).

    Entailment:
    - **PERMITTED** iff ``G ∧ ¬is-permitted(sim_tc)`` is UNSAT.
    - **DENIED** iff ``G ∧ is-permitted(sim_tc)`` is UNSAT.
    - Otherwise **AMBIGUOUS**.
    """

    def __init__(self, policy_path: Path | str | None = None) -> None:
        from z3 import parse_smt2_string

        path = Path(policy_path) if policy_path is not None else default_guardrails_policy_path()
        self.policy_path = path
        self._policy_text = path.read_text(encoding="utf-8")
        sample = parse_smt2_string(self._policy_text)
        _find_func_decl(sample, "is-permitted")

    def decide(self, scenario: GuardrailsScenario) -> GuardrailsDecision:
        import uuid
        from z3 import Not, Solver, unknown, unsat, parse_smt2_string

        suf = "_" + uuid.uuid4().hex[:8]
        frag = scenario.to_smt2_fragment(instance_suffix=suf)
        combined = self._policy_text + "\n" + frag
        all_a = parse_smt2_string(combined)
        perm_decl = _find_func_decl(all_a, "is-permitted")
        slv = Solver()
        for a in all_a:
            slv.add(a)
        try:
            sim_tc = _find_const_in_assertions(all_a, f"sim_tc{suf}")
        except ValueError as e:
            return GuardrailsDecision(GuardrailsVerdict.AMBIGUOUS, str(e))
        perm_app = perm_decl(sim_tc)

        r0 = slv.check()
        if r0 == unknown:
            return GuardrailsDecision(
                GuardrailsVerdict.AMBIGUOUS,
                "Z3 returned unknown for policy+scenario satisfiability",
            )
        if r0 == unsat:
            return GuardrailsDecision(
                GuardrailsVerdict.AMBIGUOUS,
                "Policy+scenario is UNSAT (inconsistent grounding; not a legal partial state)",
            )

        slv.push()
        slv.add(Not(perm_app))
        r1 = slv.check()
        slv.pop()

        if r1 == unknown:
            return GuardrailsDecision(
                GuardrailsVerdict.AMBIGUOUS,
                "Z3 returned unknown for ¬is-permitted query",
            )
        if r1 == unsat:
            return GuardrailsDecision(
                GuardrailsVerdict.PERMITTED,
                "Policy+scenario entails is-permitted(sim_tc)",
            )

        slv.push()
        slv.add(perm_app)
        r2 = slv.check()
        slv.pop()

        if r2 == unknown:
            return GuardrailsDecision(
                GuardrailsVerdict.AMBIGUOUS,
                "Z3 returned unknown for is-permitted query",
            )
        if r2 == unsat:
            return GuardrailsDecision(
                GuardrailsVerdict.DENIED,
                "Policy+scenario entails not is-permitted(sim_tc)",
            )
        return GuardrailsDecision(
            GuardrailsVerdict.AMBIGUOUS,
            "Both is-permitted and not is-permitted are consistent with the scenario",
        )


def decide_guardrails(
    scenario: GuardrailsScenario,
    *,
    policy_path: Path | str | None = None,
) -> GuardrailsDecision:
    """Convenience: one-shot checker (parses policy each call — prefer :class:`GuardrailsPolicyChecker`)."""

    return GuardrailsPolicyChecker(policy_path=policy_path).decide(scenario)
