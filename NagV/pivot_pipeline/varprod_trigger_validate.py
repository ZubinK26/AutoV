"""Deterministic check: varprod operands must appear in LOGICAL_IMPLICATION trigger (pipeline convention)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pivot_pipeline.linearize_rules import linearize_rules_for_cross_critic


def varprod_skip_rule_ids_from_env() -> set[str]:
    raw = os.environ.get("PIVOT_VARPROD_TRIGGER_SKIP_RULE_IDS", "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def collect_variables_in_condition(cond: Any) -> set[str]:
    if not isinstance(cond, dict):
        return set()
    k = cond.get("kind")
    if k == "atom":
        v = cond.get("variable")
        return {v} if isinstance(v, str) and v else set()
    if k == "varcmp":
        out: set[str] = set()
        for key in ("left_variable", "right_variable"):
            v = cond.get(key)
            if isinstance(v, str) and v:
                out.add(v)
        return out
    if k == "varprod_cmp":
        out = set()
        for key in ("left_variable", "right_variable"):
            v = cond.get(key)
            if isinstance(v, str) and v:
                out.add(v)
        rhs = cond.get("rhs")
        if isinstance(rhs, dict) and rhs.get("kind") == "var":
            rv = rhs.get("variable")
            if isinstance(rv, str) and rv:
                out.add(rv)
        return out
    if k in ("and", "or"):
        acc: set[str] = set()
        for ch in cond.get("children") or []:
            acc |= collect_variables_in_condition(ch)
        return acc
    if k == "not":
        return collect_variables_in_condition(cond.get("child"))
    return set()


def iter_varprod_factor_pairs(cond: Any) -> list[tuple[str, str]]:
    if not isinstance(cond, dict):
        return []
    k = cond.get("kind")
    if k == "varprod_cmp":
        lv = cond.get("left_variable")
        rv = cond.get("right_variable")
        if isinstance(lv, str) and isinstance(rv, str) and lv and rv:
            return [(lv, rv)]
        return []
    if k in ("and", "or"):
        out: list[tuple[str, str]] = []
        for ch in cond.get("children") or []:
            out.extend(iter_varprod_factor_pairs(ch))
        return out
    if k == "not":
        return iter_varprod_factor_pairs(cond.get("child"))
    return []


def _required_has_varprod(rule: dict[str, Any]) -> bool:
    if rule.get("template_class") != "LOGICAL_IMPLICATION":
        return False
    req = rule.get("required_condition")
    return bool(iter_varprod_factor_pairs(req))


def rules_with_varprod_in_required(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rules if _required_has_varprod(r)]


def linearize_varprod_rules_excerpt(rules: list[dict[str, Any]]) -> str:
    subset = rules_with_varprod_in_required(rules)
    if not subset:
        return ""
    return linearize_rules_for_cross_critic(subset)


def validate_varprod_triggers(
    rules: list[dict[str, Any]],
    *,
    skip_rule_ids: set[str] | None = None,
) -> list[str]:
    """
    For each ``LOGICAL_IMPLICATION`` whose ``required_condition`` contains ``varprod_cmp``,
    require **both** factor variables to appear somewhere in ``trigger_condition``.

    Returns a list of human-readable issue strings (empty if ok).
    """
    skip = skip_rule_ids or set()
    issues: list[str] = []
    for rule in rules:
        if rule.get("template_class") != "LOGICAL_IMPLICATION":
            continue
        rid = str(rule.get("rule_id") or "")
        if rid in skip:
            continue
        req = rule.get("required_condition")
        trig = rule.get("trigger_condition")
        pairs = iter_varprod_factor_pairs(req)
        if not pairs:
            continue
        trig_vars = collect_variables_in_condition(trig)
        for left, right in pairs:
            missing: list[str] = []
            if left not in trig_vars:
                missing.append(left)
            if right not in trig_vars:
                missing.append(right)
            if missing:
                issues.append(
                    f"{rid}: varprod factors {left!r}, {right!r} — trigger must reference "
                    f"each factor (missing from trigger: {', '.join(missing)})"
                )
    return issues


def write_ir_structure_check(work_dir: Path, ok: bool, issues: list[str]) -> None:
    path = work_dir / "ir_structure_check.json"
    path.write_text(
        json.dumps(
            {"ok": ok, "issues": issues, "check_id": "varprod_operands_in_trigger"},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


__all__ = [
    "collect_variables_in_condition",
    "iter_varprod_factor_pairs",
    "linearize_varprod_rules_excerpt",
    "rules_with_varprod_in_required",
    "validate_varprod_triggers",
    "varprod_skip_rule_ids_from_env",
    "write_ir_structure_check",
]
