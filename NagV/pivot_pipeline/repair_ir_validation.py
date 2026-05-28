"""Post-merge repair validation: sanitize audit, focus-rule change checks, K_OF_N wiring."""

from __future__ import annotations

import json
import re
from typing import Any

from pivot_pipeline.ir import sanitize_rule_dict, sanitize_rules_jsonable
from pivot_pipeline.tester_repairer_agent import precompile_repaired_rules

# Top-level keys repairers often add to K_OF_N that the schema does not support.
_INVALID_K_OF_N_TOP_KEYS = frozenset({"variable", "yields"})

_WIRING_CHANGE_RE = re.compile(
    r"variable|yields|assign|wire|link|result",
    re.IGNORECASE,
)


class RepairIrValidationError(ValueError):
    """Repair output failed generic IR validation before compile."""


def sanitize_rule_dict_audited(rule: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return sanitized rule and top-level keys dropped from the input."""
    clean = sanitize_rule_dict(rule)
    dropped = sorted(k for k in rule if k not in clean)
    return clean, dropped


def sanitize_rules_jsonable_audited(
    rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Sanitize all rules; map rule_id → dropped top-level keys."""
    dropped_by_id: dict[str, list[str]] = {}
    out: list[dict[str, Any]] = []
    for r in rules:
        clean, dropped = sanitize_rule_dict_audited(r)
        rid = str(clean.get("rule_id") or r.get("rule_id") or "").upper()
        if rid and dropped:
            dropped_by_id[rid] = dropped
        out.append(clean)
    return out, dropped_by_id


def _canonical_rule(rule: dict[str, Any]) -> str:
    return json.dumps(rule, sort_keys=True, ensure_ascii=False)


def _rules_by_id(rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("rule_id")).upper(): r for r in rules if r.get("rule_id")}


def k_of_n_binding_note(rule: dict[str, Any]) -> str:
    """Human-readable binding status for linearized / critic views."""
    if str(rule.get("template_class")) != "K_OF_N":
        return ""
    rv = (rule.get("result_variable") or "").strip()
    if rv:
        return f"assigns result → {rv}"
    return (
        "no result_variable — set result_variable on this K_OF_N, "
        "or add companion LOGICAL_IMPLICATION / CONSTANT_RELATIONAL rules"
    )


def validate_repair_ir_application(
    *,
    rules_before: list[dict[str, Any]],
    merged_rules: list[dict[str, Any]],
    sanitized_rules: list[dict[str, Any]],
    focus_rule_ids: list[str],
    change_summary: list[dict[str, Any]],
    dropped_by_rule_id: dict[str, list[str]],
) -> None:
    """
    Raise RepairIrValidationError when a repair round would be a silent no-op or illegal K_OF_N shape.
    """
    focus = {rid.upper() for rid in focus_rule_ids if rid}
    before_by = _rules_by_id(rules_before)
    after_by = _rules_by_id(sanitized_rules)
    merged_by = _rules_by_id(merged_rules)

    claimed_changed: set[str] = set()
    for entry in change_summary:
        if not isinstance(entry, dict):
            continue
        rid = entry.get("rule_id")
        if isinstance(rid, str) and rid.strip():
            claimed_changed.add(rid.strip().upper())

    for rid, dropped in dropped_by_rule_id.items():
        if rid not in focus:
            continue
        merged = merged_by.get(rid) or {}
        if str(merged.get("template_class")) != "K_OF_N":
            if dropped:
                raise RepairIrValidationError(
                    f"{rid}: dropped unsupported top-level keys {dropped} on a focus rule. "
                    "Use only allowlisted fields for this template_class (see repairer_ir_normative.md)."
                )
            continue
        bad = [k for k in dropped if k in _INVALID_K_OF_N_TOP_KEYS]
        if bad:
            raise RepairIrValidationError(
                f"{rid}: K_OF_N cannot use top-level {bad}. "
                "Use result_variable for aggregate booleans, or add separate LOGICAL_IMPLICATION / "
                "CONSTANT_RELATIONAL rules. Do not claim 'added variable/yields to K_OF_N' in change_summary."
            )
        if dropped:
            raise RepairIrValidationError(
                f"{rid}: dropped unsupported top-level keys {dropped} on K_OF_N focus rule."
            )

    for rid in focus:
        if rid not in claimed_changed:
            continue
        prior = before_by.get(rid)
        after = after_by.get(rid)
        if prior is None or after is None:
            continue
        if _canonical_rule(prior) == _canonical_rule(after):
            raise RepairIrValidationError(
                f"{rid}: change_summary listed this focus rule but the sanitized rule is unchanged. "
                "Emit a real edit (e.g. K_OF_N result_variable, LOGICAL_IMPLICATION companion, "
                "CONSTANT_RELATIONAL yields SATISFIED) — invalid keys are stripped silently."
            )

    for entry in change_summary:
        if not isinstance(entry, dict):
            continue
        rid = str(entry.get("rule_id") or "").upper()
        if rid not in focus:
            continue
        rule = after_by.get(rid) or {}
        if str(rule.get("template_class")) != "K_OF_N":
            continue
        if rule.get("result_variable"):
            continue
        change_text = str(entry.get("change") or "")
        if _WIRING_CHANGE_RE.search(change_text):
            raise RepairIrValidationError(
                f"{rid}: change_summary describes wiring/assignment but K_OF_N has no result_variable. "
                "Set result_variable to the aggregate boolean consumed by gatekeeper rules, or add "
                "LOGICAL_IMPLICATION / CONSTANT_RELATIONAL companion rules."
            )


def precompile_repaired_rules_validated(
    policy_id: str,
    rules: list[dict[str, Any]],
    *,
    rules_before: list[dict[str, Any]] | None = None,
    focus_rule_ids: list[str] | None = None,
    change_summary: list[dict[str, Any]] | None = None,
    skip_vnext_lowering: bool = False,
    policy_semantics_version: str | None = None,
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """
    Audit sanitize drops, validate repair effect, then pre-compile.

    Returns (compiled_rules, dropped_by_rule_id).
    """
    sanitized, dropped_by_id = sanitize_rules_jsonable_audited(rules)
    if (
        rules_before is not None
        and focus_rule_ids
        and change_summary is not None
    ):
        validate_repair_ir_application(
            rules_before=rules_before,
            merged_rules=rules,
            sanitized_rules=sanitized,
            focus_rule_ids=focus_rule_ids,
            change_summary=change_summary,
            dropped_by_rule_id=dropped_by_id,
        )
    compiled = precompile_repaired_rules(
        policy_id,
        sanitized,
        skip_vnext_lowering=skip_vnext_lowering,
        policy_semantics_version=policy_semantics_version,
    )
    return compiled, dropped_by_id


def compile_validation_hint(exc: BaseException) -> str:
    """Extra prompt hint for repairer retry after RepairIrValidationError."""
    msg = str(exc)
    if "result_variable" in msg or "K_OF_N" in msg:
        return (
            "\n**K_OF_N wiring:** Use optional `result_variable` on the K_OF_N rule for the aggregate "
            "boolean gatekeepers reference, and/or add LOGICAL_IMPLICATION + CONSTANT_RELATIONAL "
            "companion rules. Never put `variable` or `yields` on K_OF_N — they are stripped.\n"
        )
    if "unchanged" in msg.lower():
        return (
            "\n**No-op repair:** Your last output did not change focus rules after sanitize. "
            "Emit concrete IR edits, not narrative-only change_summary.\n"
        )
    return ""


__all__ = [
    "RepairIrValidationError",
    "compile_validation_hint",
    "k_of_n_binding_note",
    "precompile_repaired_rules_validated",
    "sanitize_rule_dict_audited",
    "sanitize_rules_jsonable_audited",
    "validate_repair_ir_application",
]
