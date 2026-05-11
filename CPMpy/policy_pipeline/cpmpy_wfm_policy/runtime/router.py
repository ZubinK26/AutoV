"""Route rules to Pattern A or B from manifest; combined gating (Project_Spec §7)."""

from __future__ import annotations

from typing import Any, Literal

from cpmpy_wfm_policy.pipeline.ast_validator import global_constraints_from_namespace
from cpmpy_wfm_policy.runtime.decision import Decision
from cpmpy_wfm_policy.runtime.pattern_a import gate_scalar_rules
from cpmpy_wfm_policy.runtime.pattern_b import PatternBError, gate_pattern_b_rules


class RouterError(ValueError):
    """Manifest routing inconsistent with rule flags."""


def assert_manifest_routing_consistent(manifest: dict[str, Any]) -> None:
    """
    §15 / §7 — pattern A iff not (global or vector); misroute raises.
    """
    rules = manifest.get("rules")
    if not isinstance(rules, list):
        raise RouterError("manifest missing rules array")
    for r in rules:
        if not isinstance(r, dict):
            raise RouterError("invalid rule entry")
        rid = r.get("id")
        ug = bool(r.get("uses_global_constraints"))
        uv = bool(r.get("uses_vector_variables"))
        pat = r.get("pattern")
        expect: Literal["A", "B"] = "B" if (ug or uv) else "A"
        if pat != expect:
            raise RouterError(
                f"routing misroute for {rid!r}: pattern {pat!r} != expected {expect!r}"
            )


def partition_rules_by_manifest(
    all_rules: dict[str, Any],
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    assert_manifest_routing_consistent(manifest)
    a: dict[str, Any] = {}
    b: dict[str, Any] = {}
    for r in manifest["rules"]:
        rid = r["id"]
        if rid not in all_rules:
            raise RouterError(f"manifest rule {rid!r} missing from policy rules dict")
        pat = r["pattern"]
        if pat == "A":
            a[rid] = all_rules[rid]
        else:
            b[rid] = all_rules[rid]
    return a, b


def gate_tool(
    *,
    all_rules: dict[str, Any],
    manifest: dict[str, Any],
    state: dict[str, int | bool],
    signature_namespace: dict[str, Any],
    pattern_b_solver: str = "z3",
) -> Decision:
    """
    Evaluate all rules: Pattern A subset first, then Pattern B with ``GLOBAL_CONSTRAINTS``.
    BLOCK if any path reports violations.
    """
    assert_manifest_routing_consistent(manifest)
    rules_a, rules_b = partition_rules_by_manifest(all_rules, manifest)
    globals_cons = global_constraints_from_namespace(signature_namespace)

    ok_a, viol_a, t_a = gate_scalar_rules(rules_a, state)
    if not ok_a:
        return Decision(
            allow=False,
            violated_rules=viol_a,
            pattern_used="A",
            explanation="scalar rules violated",
            solver_time_ms=t_a,
        )

    try:
        ok_b, viol_b, t_b = gate_pattern_b_rules(
            rules_b,
            state,
            globals_cons,
            solver=pattern_b_solver,
        )
    except PatternBError as e:
        return Decision(
            allow=False,
            violated_rules=sorted(rules_b.keys()),
            pattern_used="B",
            explanation=str(e),
            solver_time_ms=0.0,
        )

    if not ok_b:
        return Decision(
            allow=False,
            violated_rules=viol_b,
            pattern_used="B",
            explanation="pattern B rules unsat under state",
            solver_time_ms=t_a + t_b,
        )

    pat_used: Literal["A", "B"] = "B" if rules_b else "A"
    return Decision(
        allow=True,
        violated_rules=[],
        pattern_used=pat_used,
        explanation="ok",
        solver_time_ms=t_a + t_b,
    )
