"""Deterministic one-line-per-rule linearization for CrossCritic (no LLM)."""

from __future__ import annotations

import json
from typing import Any, Mapping


def _scalar(v: Any) -> str:
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        if v and all(c.isalnum() or c == "_" for c in v):
            return v
        return json.dumps(v, ensure_ascii=False)
    return json.dumps(v, ensure_ascii=False)


def _format_condition(c: Mapping[str, Any] | Any) -> str:
    if not isinstance(c, Mapping):
        return str(c)
    k = c.get("kind")
    if k == "atom":
        return f"{c['variable']} {c['operator']} {_scalar(c['value'])}"
    if k == "varcmp":
        return f"{c['left_variable']} {c['operator']} {c['right_variable']}"
    if k == "varprod_cmp":
        rhs = c.get("rhs") or {}
        if rhs.get("kind") == "var":
            rhs_s = rhs.get("variable", "")
        elif rhs.get("kind") == "const":
            rhs_s = str(rhs.get("value"))
        else:
            rhs_s = json.dumps(rhs, ensure_ascii=False)
        return (
            f"({c['left_variable']} * {c['right_variable']}) "
            f"{c['operator']} {rhs_s}"
        )
    if k == "and":
        ch = c.get("children") or []
        inner = " AND ".join(_format_condition(x) for x in ch)
        return f"({inner})" if len(ch) != 1 else inner
    if k == "or":
        ch = c.get("children") or []
        inner = " OR ".join(_format_condition(x) for x in ch)
        return f"({inner})" if len(ch) != 1 else inner
    if k == "not":
        return f"NOT ({_format_condition(c.get('child'))})"
    return json.dumps(c, ensure_ascii=False)


def _linearize_one(rule: Mapping[str, Any]) -> str:
    rid = rule.get("rule_id", "?")
    tc = rule.get("template_class", "?")

    if tc == "CONSTANT_RELATIONAL":
        y = rule.get("yields", "")
        return (
            f"{rid} | {tc} | {rule['variable']} {rule['relational_operator']} "
            f"{_scalar(rule['constant_value'])} | yields {y}"
        )
    if tc == "VARIABLE_RELATIONAL":
        y = rule.get("yields", "")
        return (
            f"{rid} | {tc} | {rule['left_variable']} {rule['relational_operator']} "
            f"{rule['right_variable']} | yields {y}"
        )
    if tc == "SET_INCLUSION":
        y = rule.get("yields", "")
        vals = rule.get("constant_array") or []
        shown = "[" + ", ".join(_scalar(x) for x in vals) + "]"
        return f"{rid} | {tc} | {rule['variable']} {rule['inclusion_operator']} {shown} | yields {y}"
    if tc == "ARITHMETIC_EVALUATION":
        y = rule.get("yields", "")
        op2 = rule.get("operand_2")
        op2s = op2 if isinstance(op2, str) else _scalar(op2)
        lim = rule.get("target_limit")
        lims = lim if isinstance(lim, str) else _scalar(lim)
        return (
            f"{rid} | {tc} | ({rule['operand_1']} {rule['math_operator']} {op2s}) "
            f"{rule['relational_operator']} {lims} | yields {y}"
        )
    if tc == "LOGICAL_IMPLICATION":
        tr = _format_condition(rule["trigger_condition"])
        req = _format_condition(rule["required_condition"])
        return f"{rid} | {tc} | IF {tr} THEN {req}"
    if tc == "PREEMPTION":
        pc = _format_condition(rule["preempting_condition"])
        act = rule.get("action", "")
        tgt = rule.get("target_rule_id")
        tgt_s = tgt if tgt else "(none)"
        return f"{rid} | {tc} | IF {pc} THEN {act} target {tgt_s}"
    if tc == "EXCLUSIVE_CHOICE":
        mode = rule.get("mode", "")
        vs = rule.get("variables") or []
        vs_s = ", ".join(str(x) for x in vs)
        return f"{rid} | {tc} | mode={mode} variables=[{vs_s}]"
    if tc == "LOGICAL_IFF":
        return (
            f"{rid} | {tc} | IFF {_format_condition(rule['left'])} "
            f"<=> {_format_condition(rule['right'])}"
        )
    return f"{rid} | {tc} | {json.dumps(rule, ensure_ascii=False)}"


def linearize_rules_for_cross_critic(rules: list[dict[str, Any]]) -> str:
    """
    Build a stable, human-readable line-per-rule view for CrossCritic.

    Variable names and template classes are preserved; order matches ``rules``.
    """
    lines = [
        "LINEARIZED MODEL (from rules_extracted.json; 1 line = 1 rule)",
        "",
    ]
    for r in rules:
        lines.append(_linearize_one(r))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = ["linearize_rules_for_cross_critic"]
