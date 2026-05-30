"""IR-derived grounded vs derived variable tiers (domain-agnostic)."""

from __future__ import annotations

from typing import Any, Literal

from pivot_pipeline.ir import MetaScheme

Tier = Literal["grounded", "derived"]


def _walk_atom_vars(
    obj: Any,
    *,
    out: set[str],
    sorts: dict[str, str] | None = None,
    sort_filter: Literal["any", "int", "bool"] = "any",
) -> None:
    if isinstance(obj, dict):
        if obj.get("kind") == "atom" and isinstance(obj.get("variable"), str):
            name = obj["variable"]
            if sort_filter == "any":
                out.add(name)
            elif sorts is not None:
                sk = sorts.get(name)
                if sort_filter == "int" and sk == "int":
                    out.add(name)
                elif sort_filter == "bool" and sk == "bool":
                    out.add(name)
        elif obj.get("kind") in ("and", "or"):
            for c in obj.get("children") or []:
                _walk_atom_vars(c, out=out, sorts=sorts, sort_filter=sort_filter)
        elif obj.get("kind") == "not":
            _walk_atom_vars(obj.get("child"), out=out, sorts=sorts, sort_filter=sort_filter)
        else:
            for v in obj.values():
                _walk_atom_vars(v, out=out, sorts=sorts, sort_filter=sort_filter)
    elif isinstance(obj, list):
        for it in obj:
            _walk_atom_vars(it, out=out, sorts=sorts, sort_filter=sort_filter)


def _collect_trigger_vars(rule: dict[str, Any], *, triggers: set[str]) -> None:
    for key in ("trigger_condition", "preempting_condition", "left", "right"):
        if key in rule:
            _walk_atom_vars(rule[key], out=triggers)
    for c in rule.get("clauses") or []:
        if isinstance(c, dict):
            _walk_atom_vars(c, out=triggers)
    for t in rule.get("terms") or []:
        if isinstance(t, dict) and isinstance(t.get("variable"), str):
            triggers.add(t["variable"])


def _collect_evidence_vars(rules: list[dict[str, Any]], sorts: dict[str, str]) -> set[str]:
    """Document-bound vars: triggers, clauses, const facts, and atoms in required_condition."""
    evidence: set[str] = set()
    for r in rules:
        if not isinstance(r, dict):
            continue
        tc = str(r.get("template_class", ""))
        _collect_trigger_vars(r, triggers=evidence)
        if "required_condition" in r:
            _walk_atom_vars(
                r["required_condition"],
                out=evidence,
                sorts=sorts,
                sort_filter="any",
            )
        if tc == "CONSTANT_RELATIONAL":
            v = r.get("variable")
            if isinstance(v, str):
                evidence.add(v)
    return evidence


def classify_variable_tiers(
    rules: list[dict[str, Any]],
    sorts: dict[str, str],
) -> dict[str, Tier]:
    """
    Classify each catalog variable as grounded (document-bound) or derived (rule output).

    Derived (v1): K_OF_N ``result_variable`` plus bool verdict flags that appear only as
    rule outputs, not as evidence atoms anywhere in the policy IR.
    """
    evidence = _collect_evidence_vars(rules, sorts)
    k_of_n_results: set[str] = set()

    for r in rules:
        if not isinstance(r, dict):
            continue
        if str(r.get("template_class", "")) == "K_OF_N":
            rv = r.get("result_variable")
            if isinstance(rv, str) and rv.strip():
                k_of_n_results.add(rv.strip())

    derived: set[str] = set(k_of_n_results)
    for name in sorted(sorts.keys()):
        if sorts.get(name) == "bool" and name not in evidence:
            derived.add(name)

    tiers: dict[str, Tier] = {}
    for name in sorted(sorts.keys()):
        tiers[name] = "derived" if name in derived else "grounded"
    return tiers


def tiers_for_meta(meta: MetaScheme, rules: list[dict[str, Any]]) -> dict[str, Tier]:
    sorts = dict(meta.variable_sorts)
    return classify_variable_tiers(rules, sorts)


__all__ = ["Tier", "classify_variable_tiers", "tiers_for_meta"]
