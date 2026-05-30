"""Deterministic template-repair strategies from failure bundles (no example-specific rules)."""

from __future__ import annotations

from typing import Any, Literal

from pivot_pipeline.repair_ir_validation import RepairIrValidationError

RepairStrategy = Literal[
    "counterfactual_require_enforced_obligation",
    "counterfactual_avoid_implication_on_mutant_pins",
    "counterfactual_other",
    "template_golden_no_ir",
    "vacuous_k_of_n_enforce",
    "variable_collision_split",
    "trigger_inconsistency_globalize",
    "other_policy_ir",
]

_STRATEGY_PRIORITY: tuple[RepairStrategy, ...] = (
    "counterfactual_avoid_implication_on_mutant_pins",
    "counterfactual_require_enforced_obligation",
    "vacuous_k_of_n_enforce",
    "variable_collision_split",
    "trigger_inconsistency_globalize",
    "counterfactual_other",
    "other_policy_ir",
    "template_golden_no_ir",
)


def _detail_text(bundle: dict[str, Any]) -> str:
    diff = bundle.get("diff")
    if isinstance(diff, dict):
        return str(diff.get("detail") or diff.get("message") or "")
    return ""


def infer_repair_strategy_from_bundle(bundle: dict[str, Any]) -> RepairStrategy:
    """Map one failure bundle row to a stable repair strategy (executor-driven)."""
    kind = str(bundle.get("template_kind") or "")
    verdict = str(bundle.get("verdict") or "")
    actual = bundle.get("actual") if isinstance(bundle.get("actual"), dict) else {}
    detail = _detail_text(bundle).lower()

    if kind == "rule_attribution":
        return "template_golden_no_ir"

    if kind == "counterfactual_flip":
        z3m = str(actual.get("z3_status_mutant") or "").lower()
        if verdict == "inconclusive" and (z3m == "unsat" or "unsat" in detail or "mutant unsat" in detail):
            return "counterfactual_avoid_implication_on_mutant_pins"
        if verdict == "fail" and (
            "flip" in detail
            or "mismatch" in detail
            or actual.get("base_decision") == actual.get("mutant_decision")
        ):
            return "counterfactual_require_enforced_obligation"
        return "counterfactual_other"

    if kind in ("decision_query", "scenario", "sat_unsat", "boundary", "pairwise"):
        if verdict == "fail" and ("vacuous" in detail or "k_of_n" in detail or "k-of-n" in detail):
            return "vacuous_k_of_n_enforce"
        return "other_policy_ir"

    return "other_policy_ir"


def strategy_for_finding(
    finding: dict[str, Any],
    bundles_by_instance: dict[str, dict[str, Any]],
) -> RepairStrategy | None:
    """Pick highest-priority strategy from instance ids cited on a finding."""
    strategies: list[RepairStrategy] = []
    for iid in finding.get("instance_ids") or []:
        b = bundles_by_instance.get(str(iid))
        if b:
            strategies.append(infer_repair_strategy_from_bundle(b))
    if not strategies:
        cat = str(finding.get("category") or "")
        if cat == "vacuous_k_of_n":
            return "vacuous_k_of_n_enforce"
        if cat == "variable_collision":
            return "variable_collision_split"
        if cat == "trigger_inconsistency":
            return "trigger_inconsistency_globalize"
        if finding.get("blame") == "template_golden":
            return "template_golden_no_ir"
        if finding.get("blame") == "policy_ir":
            return "other_policy_ir"
        return None
    chosen = strategies[0]
    best_pri = len(_STRATEGY_PRIORITY)
    for s in strategies:
        try:
            pri = _STRATEGY_PRIORITY.index(s)
        except ValueError:
            pri = len(_STRATEGY_PRIORITY)
        if pri < best_pri:
            best_pri = pri
            chosen = s
    return chosen


def enrich_findings_with_strategies(
    findings: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_inst = {str(b.get("instance_id", "")): b for b in bundles if b.get("instance_id")}
    out: list[dict[str, Any]] = []
    for f in findings:
        row = dict(f)
        strat = strategy_for_finding(row, by_inst)
        if strat:
            row["repair_strategy"] = strat
        out.append(row)
    return out


def _is_role_triggered_implication(rule: dict[str, Any]) -> bool:
    if str(rule.get("template_class")) != "LOGICAL_IMPLICATION":
        return False
    trig = rule.get("trigger_condition")
    if not isinstance(trig, dict):
        return False
    if trig.get("kind") != "atom":
        return False
    var = str(trig.get("variable") or "").lower()
    return var in ("is_candidate", "applicant_position", "is_applicant")


def validate_template_repair_transition(
    *,
    rules_before: list[dict[str, Any]],
    rules_after: list[dict[str, Any]],
    focus_rule_ids: list[str],
    strategies_by_rule: dict[str, RepairStrategy],
) -> None:
    """
    Reject repairer output that swaps between known-bad encodings for counterfactual tests.
    """
    before = {str(r.get("rule_id", "")).upper(): r for r in rules_before if r.get("rule_id")}
    after = {str(r.get("rule_id", "")).upper(): r for r in rules_after if r.get("rule_id")}
    focus = {rid.upper() for rid in focus_rule_ids if rid}

    for rid in focus:
        strat = strategies_by_rule.get(rid) or strategies_by_rule.get(rid.upper())
        if not strat:
            continue
        new = after.get(rid)
        if not new:
            continue
        if strat in (
            "counterfactual_avoid_implication_on_mutant_pins",
            "counterfactual_require_enforced_obligation",
            "vacuous_k_of_n_enforce",
        ):
            if _is_role_triggered_implication(new):
                raise RepairIrValidationError(
                    f"{rid}: repair_strategy={strat} forbids LOGICAL_IMPLICATION with "
                    "role/world trigger (is_candidate / applicant_position). Use K_OF_N with "
                    "result_variable and compile lowering, or a global obligation that allows "
                    "mutant worlds to be SAT with rule unsatisfied — not world UNSAT."
                )
        if strat in (
            "counterfactual_require_enforced_obligation",
            "vacuous_k_of_n_enforce",
        ):
            if str(new.get("template_class")) == "K_OF_N" and not str(
                new.get("result_variable") or ""
            ).strip():
                raise RepairIrValidationError(
                    f"{rid}: repair_strategy={strat} requires K_OF_N with non-empty "
                    "result_variable so the obligation can be enforced (Way B)."
                )


_VERDICT_RANK = {"pass": 0, "fail": 1, "inconclusive": 2, "error": 3}


def subset_issue_count(
    report: dict[str, Any],
    instance_ids: set[str],
) -> int:
    """Count fail + inconclusive for given instance ids."""
    n = 0
    for row in report.get("results") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instance_id", "")) not in instance_ids:
            continue
        if row.get("verdict") in ("fail", "inconclusive"):
            n += 1
    return n


def subset_worst_verdict_rank(
    report: dict[str, Any],
    instance_ids: set[str],
) -> int:
    """Worst verdict rank among target instances (pass=0 … error=3)."""
    worst = 0
    for row in report.get("results") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instance_id", "")) not in instance_ids:
            continue
        verdict = str(row.get("verdict") or "")
        worst = max(worst, _VERDICT_RANK.get(verdict, 3))
    return worst


def repair_improved_subset(
    *,
    before_report: dict[str, Any],
    after_report: dict[str, Any],
    instance_ids: set[str],
) -> bool:
    """
    True when approved template instances strictly improved.

    Prefer verdict quality (pass > fail > inconclusive) so inconclusive→fail counts
    as progress even when fail+inconclusive count is unchanged; also accept a lower
    issue count when ranks are equal.
    """
    if not instance_ids:
        return True
    before_rank = subset_worst_verdict_rank(before_report, instance_ids)
    after_rank = subset_worst_verdict_rank(after_report, instance_ids)
    if after_rank < before_rank:
        return True
    if after_rank > before_rank:
        return False
    before_n = subset_issue_count(before_report, instance_ids)
    after_n = subset_issue_count(after_report, instance_ids)
    return after_n < before_n


def strategies_by_focus_rule(
    findings: list[dict[str, Any]],
    bundles: list[dict[str, Any]],
) -> dict[str, RepairStrategy]:
    enriched = enrich_findings_with_strategies(findings, bundles)
    by_inst = {str(b.get("instance_id", "")): b for b in bundles if b.get("instance_id")}
    out: dict[str, RepairStrategy] = {}
    for f in enriched:
        strat = f.get("repair_strategy") or strategy_for_finding(f, by_inst)
        if not strat or strat == "template_golden_no_ir":
            continue
        for rid in f.get("rule_ids") or []:
            if isinstance(rid, str) and rid.strip():
                key = rid.strip().upper()
                prev = out.get(key)
                if prev is None:
                    out[key] = strat
                    continue
                try:
                    if _STRATEGY_PRIORITY.index(strat) < _STRATEGY_PRIORITY.index(prev):
                        out[key] = strat
                except ValueError:
                    out[key] = strat
    return out


__all__ = [
    "RepairStrategy",
    "enrich_findings_with_strategies",
    "infer_repair_strategy_from_bundle",
    "repair_improved_subset",
    "strategies_by_focus_rule",
    "subset_issue_count",
    "subset_worst_verdict_rank",
    "validate_template_repair_transition",
]
