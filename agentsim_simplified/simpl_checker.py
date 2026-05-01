"""Z3: ``policy_model_refined_simpl.smt2`` + :class:`RefundCallScenario` -> permit / deny / ambiguous."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from agentsim_simplified.policy_source import default_refined_policy_path
from agentsim_simplified.simpl_scenario import RefundCallScenario


class SimplVerdict(str, Enum):
    PERMITTED = "permitted"
    DENIED = "denied"
    AMBIGUOUS = "ambiguous"


# Parsed ``policy_model_refined_simpl.smt2`` yields this many top-level assertions (file order).
_POLICY_ASSERT_COUNT = 29
# First 18: structural / totality / wiring — included in cores only when Z3 needs them.
_POLICY_BG_LABELS = [f"policy_bg_{i}" for i in range(18)]
_POLICY_RULE_LABELS = [
    "rule_customer_must_exist_in_db",
    "rule_account_must_exist_in_db",
    "rule_transaction_must_exist_in_db",
    "rule_transaction_must_be_posted",
    "rule_failed_kyc",
    "rule_sanctions_block",
    "rule_merchant_amount_exceeds_original",
    "rule_goodwill_credit_exceeds_cap",
    "rule_goodwill_rolling_window_exceeded",
    "rule_vulnerable_customer_refund_cap",
    "rule_positive_completion",
]
assert len(_POLICY_BG_LABELS) + len(_POLICY_RULE_LABELS) == _POLICY_ASSERT_COUNT

QUERY_ASSUME_IS_PERMITTED = "query_assume_is_permitted"
QUERY_ASSUME_NOT_PERMITTED = "query_assume_not_permitted"


class SimplDecision:
    __slots__ = ("verdict", "detail", "unsat_core")

    def __init__(
        self,
        verdict: SimplVerdict,
        detail: str = "",
        *,
        unsat_core: frozenset[str] | None = None,
    ) -> None:
        self.verdict = verdict
        self.detail = detail
        self.unsat_core = unsat_core

    def permitted(self) -> bool:
        return self.verdict == SimplVerdict.PERMITTED


def _find_func_decl(assertions: list, name: str):
    from z3 import is_app, is_quantifier

    seen: dict[tuple[str, int], object] = {}

    def visit2(e) -> None:
        if is_app(e):
            d = e.decl()
            key = (d.name(), d.arity())
            if key[0] == name and key[1] > 0:
                seen[key] = d
            for ch in e.children():
                visit2(ch)
        elif is_quantifier(e):
            visit2(e.body())

    for a in assertions:
        visit2(a)
    for (_n, _arity), d in seen.items():
        if _n == name:
            return d
    msg = f"no function declaration named {name!r} found in policy"
    raise ValueError(msg)


def _find_const(assertions: list, cname: str):
    from z3 import is_app, is_const, is_quantifier

    def visit(e) -> object | None:
        if is_const(e) and e.decl().name() == cname:
            return e
        if is_app(e):
            for ch in e.children():
                hit = visit(ch)
                if hit is not None:
                    return hit
        elif is_quantifier(e):
            return visit(e.body())
        return None

    for a in assertions:
        hit = visit(a)
        if hit is not None:
            return hit
    msg = f"no constant {cname!r} found in assertions"
    raise ValueError(msg)


class SimplPolicyChecker:
    """
    Entailment on ``is-permitted(sim_r)``:

    - **PERMITTED** if ``G`` SAT and ``G + not is-permitted(sim_r)`` UNSAT
    - **DENIED** if ``G`` SAT and ``G + is-permitted(sim_r)`` UNSAT
    - **AMBIGUOUS** otherwise (or ``G`` UNSAT / unknown)

    Use ``decide(..., unsat_core=True)`` to populate :attr:`SimplDecision.unsat_core` with tracker
    names for the entailment query that succeeded (subset of tracked axioms; Z3 may minimize).
    """

    def __init__(self, policy_path: Path | str | None = None) -> None:
        from z3 import parse_smt2_string

        path = Path(policy_path) if policy_path is not None else default_refined_policy_path()
        self.policy_path = path
        self._policy_text = path.read_text(encoding="utf-8")
        sample = parse_smt2_string(self._policy_text)
        _find_func_decl(sample, "is-permitted")
        if len(sample) != _POLICY_ASSERT_COUNT:
            msg = (
                f"policy assertion count mismatch: expected {_POLICY_ASSERT_COUNT}, "
                f"got {len(sample)} (update _POLICY_ASSERT_COUNT / labels in simpl_checker.py)"
            )
            raise ValueError(msg)

    def decide(self, scenario: RefundCallScenario, *, unsat_core: bool = False) -> SimplDecision:
        import uuid
        from z3 import Bool, Not, Solver, unknown, unsat, parse_smt2_string

        suf = "_" + uuid.uuid4().hex[:8]
        frag = scenario.to_smt2_fragment(instance_suffix=suf)
        combined = self._policy_text + "\n" + frag
        all_a = parse_smt2_string(combined)
        perm_decl = _find_func_decl(all_a, "is-permitted")
        sim_r = _find_const(all_a, f"sim_r{suf}")
        perm_app = perm_decl(sim_r)

        policy_n = _POLICY_ASSERT_COUNT
        if len(all_a) <= policy_n:
            msg = f"expected scenario assertions after policy, got {len(all_a)} total"
            raise ValueError(msg)
        policy_a = all_a[:policy_n]
        scenario_a = all_a[policy_n:]

        def track_solver() -> Solver:
            slv = Solver()
            for i, a in enumerate(policy_a):
                lab = _POLICY_BG_LABELS[i] if i < len(_POLICY_BG_LABELS) else _POLICY_RULE_LABELS[i - len(_POLICY_BG_LABELS)]
                slv.assert_and_track(a, Bool(lab))
            for j, a in enumerate(scenario_a):
                slv.assert_and_track(a, Bool(f"scenario_ground_{j}"))
            return slv

        def core_name_set(slv_tracked: Solver) -> frozenset[str]:
            c = slv_tracked.unsat_core()
            return frozenset(x.decl().name() for x in c)

        slv0 = track_solver()
        r0 = slv0.check()
        if r0 == unknown:
            return SimplDecision(SimplVerdict.AMBIGUOUS, "Z3 unknown on policy+scenario SAT")
        if r0 == unsat:
            return SimplDecision(SimplVerdict.AMBIGUOUS, "policy+scenario UNSAT (inconsistent grounding)")
        if not unsat_core:
            # Fast path: plain adds (same logic, no tracking overhead)
            slv = Solver()
            for a in all_a:
                slv.add(a)
            slv.push()
            slv.add(Not(perm_app))
            r1 = slv.check()
            slv.pop()
            if r1 == unknown:
                return SimplDecision(SimplVerdict.AMBIGUOUS, "Z3 unknown for not is-permitted query")
            if r1 == unsat:
                return SimplDecision(SimplVerdict.PERMITTED, "entails is-permitted(sim_r)")
            slv.push()
            slv.add(perm_app)
            r2 = slv.check()
            slv.pop()
            if r2 == unknown:
                return SimplDecision(SimplVerdict.AMBIGUOUS, "Z3 unknown for is-permitted query")
            if r2 == unsat:
                return SimplDecision(SimplVerdict.DENIED, "entails not is-permitted(sim_r)")
            return SimplDecision(
                SimplVerdict.AMBIGUOUS,
                "is-permitted and not is-permitted both consistent",
            )

        slv1 = track_solver()
        q1 = Bool(QUERY_ASSUME_NOT_PERMITTED)
        slv1.assert_and_track(Not(perm_app), q1)
        r1 = slv1.check()
        if r1 == unknown:
            return SimplDecision(SimplVerdict.AMBIGUOUS, "Z3 unknown for not is-permitted query")
        if r1 == unsat:
            core = core_name_set(slv1)
            return SimplDecision(
                SimplVerdict.PERMITTED,
                "entails is-permitted(sim_r)",
                unsat_core=core,
            )
        slv2 = track_solver()
        q2 = Bool(QUERY_ASSUME_IS_PERMITTED)
        slv2.assert_and_track(perm_app, q2)
        r2 = slv2.check()
        if r2 == unknown:
            return SimplDecision(SimplVerdict.AMBIGUOUS, "Z3 unknown for is-permitted query")
        if r2 == unsat:
            core = core_name_set(slv2)
            return SimplDecision(
                SimplVerdict.DENIED,
                "entails not is-permitted(sim_r)",
                unsat_core=core,
            )
        return SimplDecision(
            SimplVerdict.AMBIGUOUS,
            "is-permitted and not is-permitted both consistent",
        )
