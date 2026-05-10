"""Validate template instances against MetaScheme (variable names, golden shape hints)."""

from __future__ import annotations

from typing import Any

from pivot_pipeline.ir import MetaScheme, Preemption
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


def _vars_in_meta(meta: MetaScheme) -> set[str]:
    return set(meta.variable_sorts.keys()) if meta.variable_sorts else set()


def _ensure_vars(world: dict[str, int | bool], meta: MetaScheme, *, where: str) -> None:
    known = _vars_in_meta(meta)
    # If variable_sorts empty, infer names from rules via compile - z3 creates on demand.
    # Require explicit sorts populated: build_meta_scheme doesn't fill sorts; z3_compile uses meta.variable_sorts.
    # load_rules_and_compile may leave sorts empty - then allow any name (weak v1).
    if not known:
        return
    for v in world:
        if v not in known:
            raise ValueError(f"{where}: unknown variable {v!r} (not in meta.variable_sorts)")


def _golden_keys(kind: str, g: dict[str, Any]) -> None:
    if kind == "scenario":
        if "sat" not in g or not isinstance(g["sat"], bool):
            raise ValueError("scenario golden must have boolean 'sat'")
    elif kind == "decision_query":
        d = g.get("decision")
        if d not in ("satisfied", "unsatisfied"):
            raise ValueError("decision_query golden must have 'decision': 'satisfied' | 'unsatisfied'")
    elif kind == "rule_attribution":
        _golden_keys("decision_query", g)
        rids = g.get("rule_ids")
        if not isinstance(rids, list) or not all(isinstance(x, str) for x in rids):
            raise ValueError("rule_attribution golden must have 'rule_ids': list[str]")
    elif kind == "boundary":
        ds = g.get("decisions")
        if not isinstance(ds, list) or len(ds) != 3:
            raise ValueError("boundary golden must have 'decisions': list of 3 items")
        for x in ds:
            if x not in ("satisfied", "unsatisfied"):
                raise ValueError("boundary decisions must be satisfied/unsatisfied")
    elif kind == "counterfactual_flip":
        if g.get("mutant_unsat") is True:
            if g["base_decision"] not in ("satisfied", "unsatisfied"):
                raise ValueError("counterfactual base_decision invalid")
            if not isinstance(g.get("expect_flip"), bool):
                raise ValueError("expect_flip must be bool")
        else:
            for k in ("base_decision", "mutant_decision", "expect_flip"):
                if k not in g:
                    raise ValueError(f"counterfactual_flip golden must include {k!r}")
            if g["base_decision"] not in ("satisfied", "unsatisfied"):
                raise ValueError("counterfactual base_decision invalid")
            if g["mutant_decision"] not in ("satisfied", "unsatisfied"):
                raise ValueError("counterfactual mutant_decision invalid")
            if not isinstance(g["expect_flip"], bool):
                raise ValueError("expect_flip must be bool")
    elif kind == "obligation_inventory":
        ob = g.get("obligations")
        if not isinstance(ob, list):
            raise ValueError("obligation_inventory golden must have 'obligations': list")
        for item in ob:
            if not isinstance(item, dict) or item.get("key") is None:
                raise ValueError("each obligation must be {key: str, args: [...]}")
    elif kind == "sat_unsat":
        if g.get("expect") not in ("sat", "unsat"):
            raise ValueError("sat_unsat golden must have 'expect': 'sat' | 'unsat'")
    elif kind == "pairwise":
        if "expect_equal" in g:
            if not isinstance(g["expect_equal"], bool):
                raise ValueError("pairwise expect_equal must be bool")
        else:
            for k in ("decision_a", "decision_b"):
                if g.get(k) not in ("satisfied", "unsatisfied"):
                    raise ValueError("pairwise golden needs decision_a/decision_b or expect_equal")


def validate_query_structure(query: dict[str, Any]) -> None:
    dm = query.get("decision_metric")
    if dm == "rule":
        if not query.get("rule_id"):
            raise ValueError("query with decision_metric=rule requires rule_id")
    elif dm == "variable":
        if not query.get("variable"):
            raise ValueError("query with decision_metric=variable requires variable")
    else:
        raise ValueError("query.decision_metric must be 'rule' or 'variable'")


def validate_instance(meta: MetaScheme, inst: TemplateInstance) -> None:
    if isinstance(inst, ScenarioInstance):
        _ensure_vars(inst.world, meta, where=f"scenario {inst.instance_id}")
        _golden_keys("scenario", inst.golden)
    elif isinstance(inst, DecisionQueryInstance):
        _ensure_vars(inst.world, meta, where=f"decision_query {inst.instance_id}")
        validate_query_structure(inst.query)
        _golden_keys("decision_query", inst.golden)
    elif isinstance(inst, RuleAttributionInstance):
        _ensure_vars(inst.world, meta, where=f"rule_attribution {inst.instance_id}")
        validate_query_structure(inst.query)
        _golden_keys("rule_attribution", inst.golden)
    elif isinstance(inst, BoundaryInstance):
        merged = {**inst.world_base, inst.axis_variable: inst.values[0]}
        _ensure_vars(merged, meta, where=f"boundary {inst.instance_id}")
        validate_query_structure(inst.query)
        _golden_keys("boundary", inst.golden)
    elif isinstance(inst, CounterfactualInstance):
        _ensure_vars(inst.world_base, meta, where=f"counterfactual base {inst.instance_id}")
        _ensure_vars(inst.world_mutant, meta, where=f"counterfactual mutant {inst.instance_id}")
        validate_query_structure(inst.query)
        _golden_keys("counterfactual_flip", inst.golden)
    elif isinstance(inst, ObligationInventoryInstance):
        _ensure_vars(inst.world, meta, where=f"obligation_inventory {inst.instance_id}")
        _golden_keys("obligation_inventory", inst.golden)
    elif isinstance(inst, SatUnsatInstance):
        _ensure_vars(inst.world, meta, where=f"sat_unsat {inst.instance_id}")
        _golden_keys("sat_unsat", inst.golden)
    elif isinstance(inst, PairwiseInstance):
        wa = {**inst.world, **inst.query_a}
        wb = {**inst.world, **inst.query_b}
        _ensure_vars(wa, meta, where=f"pairwise a {inst.instance_id}")
        _ensure_vars(wb, meta, where=f"pairwise b {inst.instance_id}")
        validate_query_structure(inst.query)
        _golden_keys("pairwise", inst.golden)
    else:
        raise TypeError(inst)


def active_non_preemption_rule_ids(meta: MetaScheme) -> list[str]:
    return sorted(r.rule_id for r in meta.rules if not isinstance(r, Preemption))
