"""Focused rules payload and merge for Pivot Test-Repairer."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

_RULE_ID_RE = re.compile(r"\bR\d{4,}\b", re.IGNORECASE)
_STUB_MARKER = "_payload_stub"


class MergeRepairerOutputError(ValueError):
    """Test-Repairer output could not be merged into the full policy."""


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
                found.add(m.group(0).upper())
        for key in ("rule_id", "target_rule_id"):
            v = f.get(key)
            if isinstance(v, str) and _RULE_ID_RE.fullmatch(v.strip()):
                found.add(v.strip().upper())
        rule_ids = f.get("rule_ids")
        if isinstance(rule_ids, list):
            for rid in rule_ids:
                if isinstance(rid, str) and _RULE_ID_RE.fullmatch(rid.strip()):
                    found.add(rid.strip().upper())
        for blob_key in ("explanation", "recommendation", "nl_pointer"):
            blob = f.get(blob_key) or ""
            if isinstance(blob, str):
                for m in _RULE_ID_RE.finditer(blob):
                    found.add(m.group(0).upper())
    return sorted(found)


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


def merge_repairer_output(
    *,
    full_rules: list[dict[str, Any]],
    repairer_rules: list[dict[str, Any]],
    focus_rule_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Merge LLM output into the full policy. Stubs or unchanged mini-records keep the original rule.
    """
    focus = {rid.upper() for rid in (focus_rule_ids or [])}
    by_full = {str(r.get("rule_id")).upper(): r for r in full_rules if r.get("rule_id")}
    by_repair = {str(r.get("rule_id")).upper(): r for r in repairer_rules if r.get("rule_id")}

    missing = set(by_full) - set(by_repair)
    if missing:
        raise MergeRepairerOutputError(
            f"Test-Repairer output missing rule_id(s): {', '.join(sorted(missing))}"
        )
    extra = set(by_repair) - set(by_full)
    if extra:
        raise MergeRepairerOutputError(
            f"Test-Repairer output has unknown rule_id(s): {', '.join(sorted(extra))}"
        )

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
    "merge_repairer_output",
    "payload_rules_json_size",
]
