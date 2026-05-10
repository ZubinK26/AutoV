"""Validate override DAG and build evaluation pathways (Phase 2, v1)."""

from __future__ import annotations

from pivot_pipeline.ir import (
    AtomicRule,
    ConstantRelational,
    EvaluationPathway,
    MetaScheme,
    Preemption,
    RelationalOperator,
)


def _override_edges(rules: list[AtomicRule]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    for r in rules:
        if r.overrides:
            if r.rule_id == r.overrides:
                raise ValueError(f"{r.rule_id} cannot override itself")
            edges.append((r.rule_id, r.overrides))
    return edges


def assert_override_dag_acyclic(rules: list[AtomicRule]) -> None:
    edges = _override_edges(rules)
    adj: dict[str, list[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(u: str) -> None:
        if u in stack:
            raise ValueError(f"override cycle detected involving {u!r}")
        if u in visited:
            return
        visited.add(u)
        stack.add(u)
        for v in adj.get(u, []):
            dfs(v)
        stack.remove(u)

    nodes = {r.rule_id for r in rules}
    for _a, b in edges:
        nodes.add(b)
    for n in nodes:
        if n not in visited:
            dfs(n)


def resolve_active_rule_ids(rules: list[AtomicRule]) -> set[str]:
    by_id = {r.rule_id: r for r in rules}
    targets: dict[str, list[str]] = {}
    for r in rules:
        if r.overrides:
            if r.overrides not in by_id:
                raise ValueError(f"{r.rule_id}: overrides unknown rule {r.overrides!r}")
            targets.setdefault(r.overrides, []).append(r.rule_id)
    removed: set[str] = set()
    for target, overs in targets.items():
        winner = max(overs)
        for o in overs:
            if o != winner:
                removed.add(o)
        removed.add(target)
    return {r.rule_id for r in rules} - removed


def _resolve_symbolic_preemption_targets(rules: list[AtomicRule]) -> list[AtomicRule]:
    """
    Map legacy LLM symbolic ``target_rule_id`` strings to real ``rule_id`` when unique.

    Supported:
    - ``storage_limit_500gb`` → the sole ``CONSTANT_RELATIONAL`` on ``requested_storage_volume`` LT 500.
    """
    known = {r.rule_id for r in rules}

    def storage_lt_500_rule_id() -> str | None:
        hits = [
            r.rule_id
            for r in rules
            if isinstance(r, ConstantRelational)
            and r.variable == "requested_storage_volume"
            and r.relational_operator == RelationalOperator.LT
            and r.constant_value == 500
        ]
        return hits[0] if len(hits) == 1 else None

    out: list[AtomicRule] = []
    for r in rules:
        if isinstance(r, Preemption) and r.target_rule_id and r.target_rule_id not in known:
            tid = r.target_rule_id
            resolved: str | None = None
            if tid == "storage_limit_500gb":
                resolved = storage_lt_500_rule_id()
            if resolved:
                r = r.model_copy(update={"target_rule_id": resolved})
        out.append(r)
    return out


def build_meta_scheme(*, policy_id: str, rules: list[AtomicRule]) -> MetaScheme:
    assert_override_dag_acyclic(rules)
    rules = _resolve_symbolic_preemption_targets(rules)
    known = {r.rule_id for r in rules}
    by_id = {r.rule_id: r for r in rules}
    for r in rules:
        if isinstance(r, Preemption) and r.target_rule_id:
            tid = r.target_rule_id
            if tid not in known:
                raise ValueError(
                    f"{r.rule_id}: PREEMPTION target_rule_id {tid!r} is not a rule_id in this policy "
                    f"(use the exact rule_id of the targeted rule, not a symbolic name)."
                )
            if isinstance(by_id[tid], Preemption):
                raise ValueError(
                    f"{r.rule_id}: PREEMPTION target_rule_id {tid!r} must not reference another PREEMPTION rule."
                )
    for r in rules:
        if r.applies_to != "GLOBAL" and r.applies_to not in known:
            raise ValueError(f"{r.rule_id}: applies_to {r.applies_to!r} not found")
        if r.overrides and r.overrides not in known:
            raise ValueError(f"{r.rule_id}: overrides {r.overrides!r} not found")
    active = resolve_active_rule_ids(rules)
    for r in rules:
        if r.rule_id not in active:
            continue
        if r.applies_to != "GLOBAL" and r.applies_to not in active:
            raise ValueError(
                f"{r.rule_id}: applies_to {r.applies_to!r} is not an active rule after overrides"
            )
    must = sorted(
        r.rule_id
        for r in rules
        if r.rule_id in active and not isinstance(r, Preemption)
    )
    pw = EvaluationPathway(
        pathway_id="compiled_default",
        description="v1: single pathway AND of active rules (non-PREEMPTION) after overrides",
        must_satisfy_all=must,
        must_not_trigger=[],
    )
    return MetaScheme(policy_id=policy_id, evaluation_pathways=[pw], rules=rules)
