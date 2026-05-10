"""Compare actual executor output to golden; return verdict + diff."""

from __future__ import annotations

from typing import Any

from pivot_pipeline.template_suite.schemas import (
    BoundaryInstance,
    CounterfactualInstance,
    DecisionQueryInstance,
    ObligationInventoryInstance,
    PairwiseInstance,
    RuleAttributionInstance,
    SatUnsatInstance,
    ScenarioInstance,
    TemplateInstance,
)

Verdict = str  # pass | fail | error | inconclusive


def diff_instance(inst: TemplateInstance, actual: dict[str, Any]) -> tuple[Verdict, dict[str, Any]]:
    """Return verdict and diff detail structure."""
    diff: dict[str, Any] = {"match": True, "detail": []}

    def fail(msg: str, **extra: Any) -> tuple[Verdict, dict[str, Any]]:
        diff["match"] = False
        diff["detail"].append({"message": msg, **extra})
        return "fail", diff

    def inconc(msg: str, **extra: Any) -> tuple[Verdict, dict[str, Any]]:
        diff["match"] = False
        diff["detail"].append({"message": msg, **extra})
        return "inconclusive", diff

    if isinstance(inst, ScenarioInstance):
        if actual.get("z3_status") == "unknown":
            return inconc("z3 unknown for scenario", status=actual.get("z3_status"))
        g = bool(inst.golden["sat"])
        a = bool(actual.get("sat"))
        if g == a:
            return "pass", diff
        return fail("sat mismatch", golden=g, actual=a)

    if isinstance(inst, SatUnsatInstance):
        exp = inst.golden["expect"]
        ar = actual.get("expect_resolved")
        if ar == "unknown":
            return inconc("z3 unknown", z3_status=actual.get("z3_status"))
        if ar == exp:
            return "pass", diff
        return fail("sat/unsat mismatch", golden=exp, actual=ar)

    if isinstance(inst, DecisionQueryInstance):
        if actual.get("z3_status") != "sat":
            return inconc("world+policy not sat; cannot read decision", z3_status=actual.get("z3_status"))
        g = inst.golden["decision"]
        a = actual.get("decision")
        if a in (None, "unknown"):
            return inconc("decision unknown", actual=a)
        if g == a:
            return "pass", diff
        return fail("decision mismatch", golden=g, actual=a)

    if isinstance(inst, RuleAttributionInstance):
        if actual.get("z3_status") != "sat":
            return inconc("world+policy not sat; cannot read attribution", z3_status=actual.get("z3_status"))
        g_d = inst.golden["decision"]
        a_d = actual.get("decision")
        if a_d in (None, "unknown"):
            return inconc("decision unknown for attribution", actual=a_d)
        if g_d != a_d:
            return fail("decision mismatch (attribution)", golden=g_d, actual=a_d)
        g_ids = sorted(inst.golden["rule_ids"])
        a_ids = list(actual.get("rule_ids") or [])
        if g_ids != a_ids:
            return fail("rule_ids mismatch", golden=g_ids, actual=a_ids)
        return "pass", diff

    if isinstance(inst, BoundaryInstance):
        g = list(inst.golden["decisions"])
        a = list(actual.get("decisions") or [])
        if any(x == "unknown" for x in a):
            return inconc("boundary step unknown", decisions=a)
        if g == a:
            return "pass", diff
        return fail("boundary decisions mismatch", golden=g, actual=a)

    if isinstance(inst, CounterfactualInstance):
        g = inst.golden
        if g.get("mutant_unsat") is True:
            st_b = actual.get("z3_status_base")
            st_m = actual.get("z3_status_mutant")
            if st_b != "sat":
                return inconc("expected base sat", z3_status_base=st_b)
            if st_m != "unsat":
                return fail("expected mutant policy+world unsat", z3_status_mutant=st_m)
            ab = actual.get("base_decision")
            if ab in (None, "unknown"):
                return inconc("base decision unknown", actual=ab)
            if g["base_decision"] != ab:
                return fail("base_decision mismatch", golden=g["base_decision"], actual=ab)
            if not g.get("expect_flip", True):
                return fail("expect_flip false but mutant_unsat mode always implies flip")
            return "pass", diff

        if actual.get("z3_status_base") == "unknown" or actual.get("z3_status_mutant") == "unknown":
            return inconc("counterfactual z3 unknown", actual=actual)
        gb = inst.golden["base_decision"]
        gm = inst.golden["mutant_decision"]
        ef = inst.golden["expect_flip"]
        ab = actual.get("base_decision")
        am = actual.get("mutant_decision")
        if ab in (None, "unknown") or am in (None, "unknown"):
            return inconc("counterfactual decision unknown", base=ab, mutant=am)
        if gb != ab or gm != am:
            return fail("counterfactual decision mismatch", golden=(gb, gm), actual=(ab, am))
        flipped = ab != am
        if flipped != ef:
            return fail("expect_flip mismatch", golden=ef, actual=flipped)
        return "pass", diff

    if isinstance(inst, ObligationInventoryInstance):
        def norm(ob: list[dict]) -> list[tuple[str, tuple]]:
            out = []
            for x in ob:
                key = str(x["key"])
                args = tuple(x.get("args") or [])
                out.append((key, args))
            return sorted(out)

        g = norm(list(inst.golden["obligations"]))
        a = norm(list(actual.get("obligations") or []))
        if g == a:
            return "pass", diff
        return fail("obligations mismatch", golden=g, actual=a)

    if isinstance(inst, PairwiseInstance):
        if actual.get("z3_status_a") == "unknown" or actual.get("z3_status_b") == "unknown":
            return inconc("pairwise z3 unknown", actual=actual)
        da = actual.get("decision_a")
        db = actual.get("decision_b")
        if da in (None, "unknown") or db in (None, "unknown"):
            return inconc("pairwise decision unknown", decision_a=da, decision_b=db)
        if "expect_equal" in inst.golden:
            ok = da == db
            if inst.golden["expect_equal"]:
                if ok:
                    return "pass", diff
                return fail("expected equal decisions", decision_a=da, decision_b=db)
            if not ok:
                return "pass", diff
            return fail("expected unequal decisions", decision_a=da, decision_b=db)
        ga = inst.golden["decision_a"]
        gb = inst.golden["decision_b"]
        if da == ga and db == gb:
            return "pass", diff
        return fail("pairwise decisions mismatch", golden=(ga, gb), actual=(da, db))

    return "fail", {"match": False, "detail": [{"message": "unknown template kind"}]}
