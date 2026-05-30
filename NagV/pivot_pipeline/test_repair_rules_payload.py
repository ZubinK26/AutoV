"""Focused rules payload and merge for Pivot Test-Repairer."""

from __future__ import annotations

import copy
import json
import os
import re
from typing import Any

_RULE_ID_RE = re.compile(r"\bR(\d{4,})\b", re.IGNORECASE)
_RULE_ID_FULLMATCH = re.compile(r"^R\d{4,}$", re.IGNORECASE)
_STUB_MARKER = "_payload_stub"


class MergeRepairerOutputError(ValueError):
    """Test-Repairer output could not be merged into the full policy."""


def _rule_id_numeric(rule_id: str) -> int:
    m = _RULE_ID_RE.search(rule_id.strip())
    return int(m.group(1)) if m else 999_999


def max_rule_id_numeric(rules: list[dict[str, Any]]) -> int:
    """Highest ``R####`` numeric suffix in ``rules``, or 0."""
    best = 0
    for r in rules:
        rid = str(r.get("rule_id") or "").strip()
        m = _RULE_ID_FULLMATCH.match(rid)
        if m:
            best = max(best, _rule_id_numeric(rid))
    return best


def repair_allow_append_rules() -> bool:
    """True when ``PIVOT_REPAIR_ALLOW_APPEND_RULES`` is 1/true/yes (opt-in append merge)."""
    raw = os.getenv("PIVOT_REPAIR_ALLOW_APPEND_RULES", "").strip().lower()
    return raw in ("1", "true", "yes")


def repairer_append_payload_fields(full_rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Payload keys for Test/Cross repairer when append is enabled."""
    return {
        "allow_append_rules": True,
        "suggested_next_rule_ids": suggest_next_rule_ids(full_rules, count=4),
    }


def suggest_next_rule_ids(
    full_rules: list[dict[str, Any]],
    *,
    count: int = 3,
) -> list[str]:
    """Fresh rule ids for companion rules (e.g. ``R0010`` after ``R0009``)."""
    start = max_rule_id_numeric(full_rules) + 1
    return [f"R{n:04d}" for n in range(start, start + max(1, count))]


def focus_rule_ids_from_handoff(handoff: dict[str, Any]) -> list[str]:
    """Collect rule ids from approved findings (formal_pointer, change_summary hints, text)."""
    found: set[str] = set()
    for f in handoff.get("findings") or []:
        if not isinstance(f, dict):
            continue
        fp = (f.get("formal_pointer") or "").strip()
        if fp:
            m = _RULE_ID_RE.search(fp)
            if m:
                found.add(f"R{m.group(1)}")
        for key in ("rule_id", "target_rule_id"):
            v = f.get(key)
            if isinstance(v, str) and _RULE_ID_FULLMATCH.match(v.strip()):
                found.add(v.strip().upper())
        rule_ids = f.get("rule_ids")
        if isinstance(rule_ids, list):
            for rid in rule_ids:
                if isinstance(rid, str) and _RULE_ID_FULLMATCH.match(rid.strip()):
                    found.add(rid.strip().upper())
        for blob_key in ("explanation", "recommendation", "nl_pointer"):
            blob = f.get(blob_key) or ""
            if isinstance(blob, str):
                for m in _RULE_ID_RE.finditer(blob):
                    found.add(f"R{m.group(1)}")
    return sorted(found, key=_rule_id_numeric)


def _rule_stub(rule: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": rule.get("rule_id"),
        "template_class": rule.get("template_class"),
        "applies_to": rule.get("applies_to", "GLOBAL"),
        _STUB_MARKER: True,
    }


def build_rules_payload_stubs(
    full_rules: list[dict[str, Any]],
    focus_rule_ids: list[str],
) -> list[dict[str, Any]]:
    focus = {rid.upper() for rid in focus_rule_ids}
    out: list[dict[str, Any]] = []
    for rule in full_rules:
        rid = str(rule.get("rule_id") or "").upper()
        if rid and rid in focus:
            out.append(copy.deepcopy(rule))
        else:
            out.append(_rule_stub(rule))
    return out


def _is_unchanged_stub(repairer_rule: dict[str, Any]) -> bool:
    if repairer_rule.get(_STUB_MARKER) is True:
        return True
    keys = set(repairer_rule.keys()) - {_STUB_MARKER}
    return keys <= {"rule_id", "template_class", "applies_to"}


def repairer_rules_with_missing_stubs(
    full_rules: list[dict[str, Any]],
    repairer_rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Extend repairer output with unchanged stubs for any existing rule_id omitted by the LLM.

    Returns ``(extended_rules, sorted_missing_ids)`` where ``missing_ids`` were filled.
    """
    by_full = {str(r.get("rule_id")).upper(): r for r in full_rules if r.get("rule_id")}
    by_repair = {str(r.get("rule_id")).upper(): r for r in repairer_rules if r.get("rule_id")}
    missing = sorted(set(by_full) - set(by_repair), key=_rule_id_numeric)
    if not missing:
        return repairer_rules, []
    extended = list(repairer_rules)
    for rid in missing:
        extended.append(_rule_stub(by_full[rid]))
    return extended, missing


def merge_repairer_output(
    *,
    full_rules: list[dict[str, Any]],
    repairer_rules: list[dict[str, Any]],
    focus_rule_ids: list[str] | None = None,
    allow_append_rules: bool | None = None,
) -> list[dict[str, Any]]:
    """
    Merge LLM output into the full policy.

    - Every existing ``rule_id`` must appear in the repairer output (stub or full body).
    - When ``allow_append_rules`` is true (or ``PIVOT_REPAIR_ALLOW_APPEND_RULES=1`` when None),
      **new** ``rule_id`` values may be **appended** after existing rules.
    """
    if allow_append_rules is None:
        allow_append_rules = repair_allow_append_rules()
    focus = {rid.upper() for rid in (focus_rule_ids or [])}
    by_full = {str(r.get("rule_id")).upper(): r for r in full_rules if r.get("rule_id")}
    by_repair = {str(r.get("rule_id")).upper(): r for r in repairer_rules if r.get("rule_id")}

    missing = set(by_full) - set(by_repair)
    if missing:
        raise MergeRepairerOutputError(
            f"Repairer output missing rule_id(s): {', '.join(sorted(missing))} "
            "(include every existing rule_id as a full body or `_payload_stub` stub)."
        )

    extra = set(by_repair) - set(by_full)
    new_ids = sorted(extra, key=_rule_id_numeric)
    if extra and not allow_append_rules:
        raise MergeRepairerOutputError(
            f"Test-Repairer output has unknown rule_id(s): {', '.join(new_ids)}"
        )

    for nid in new_ids:
        rep = by_repair[nid]
        if _is_unchanged_stub(rep):
            raise MergeRepairerOutputError(
                f"New rule {nid} must be a full rule object, not a stub "
                f"(`{_STUB_MARKER}` or rule_id/template_class/applies_to only)."
            )
        if not rep.get("template_class"):
            raise MergeRepairerOutputError(f"New rule {nid} is missing template_class.")

    merged: list[dict[str, Any]] = []
    for rule in full_rules:
        rid = str(rule.get("rule_id")).upper()
        rep = by_repair[rid]
        if _is_unchanged_stub(rep):
            merged.append(copy.deepcopy(by_full[rid]))
        elif rid in focus or not rep.get(_STUB_MARKER):
            merged.append(copy.deepcopy(rep))
        else:
            merged.append(copy.deepcopy(by_full[rid]))

    for nid in new_ids:
        merged.append(copy.deepcopy(by_repair[nid]))

    return merged


def payload_rules_json_size(full_rules: list[dict[str, Any]], stubbed: list[dict[str, Any]]) -> tuple[int, int]:
    """Return (full_bytes, stubbed_bytes) for tests."""
    full_b = len(json.dumps(full_rules, ensure_ascii=False))
    stub_b = len(json.dumps(stubbed, ensure_ascii=False))
    return full_b, stub_b


__all__ = [
    "MergeRepairerOutputError",
    "build_rules_payload_stubs",
    "focus_rule_ids_from_handoff",
    "max_rule_id_numeric",
    "merge_repairer_output",
    "payload_rules_json_size",
    "repair_allow_append_rules",
    "repairer_append_payload_fields",
    "suggest_next_rule_ids",
]
