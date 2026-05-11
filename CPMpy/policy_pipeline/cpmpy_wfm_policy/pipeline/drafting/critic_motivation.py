"""Verify Critic ``motivating_rule_text`` fields against ``rules.txt`` (Sig_Agents signature_critic.md)."""

from __future__ import annotations

import re
from typing import Any

_MOTIVATION_SECTION_KEYS: dict[str, str] = {
    "missing_fields": "motivating_rule_text",
    "suspicious_bounds": "motivating_rule_text",
    "incomplete_enums": "motivating_rule_text",
}

_EXEMPT_SUBSTRINGS = frozenset(
    {
        "",
        "no rule",
        "n/a",
        "none",
        "domain knowledge",
        "domain notes",
        "domain notes excerpt",
        "not applicable",
    }
)


def _norm_ws(s: str) -> str:
    return " ".join(s.strip().split()).casefold()


def _blob_casefold(rules_text: str, domain_notes: str | None) -> str:
    parts = [rules_text, domain_notes or ""]
    return "\n".join(parts).casefold()


def _motivation_satisfied(motivation: str, blob_cf: str) -> bool:
    raw = motivation.strip()
    if not raw:
        return True
    n = _norm_ws(raw)
    if n in _EXEMPT_SUBSTRINGS:
        return True
    if n in blob_cf:
        return True
    # Allow quoted excerpts: strip outer quotes
    unq = raw.strip('"').strip("'").strip()
    if unq != raw and _norm_ws(unq) in blob_cf:
        return True
    # Minimum significant chunk: if motivation is long, require aWindow of 24 chars to appear
    compact = re.sub(r"\s+", " ", raw).casefold()
    if len(compact) >= 24 and compact[:24] in blob_cf:
        return True
    if len(compact) >= 24 and compact[-24:] in blob_cf:
        return True
    # Multimotivation: any semicolon-separated clause
    for chunk in re.split(r"[;\n]", raw):
        c = chunk.strip()
        if len(c) < 12:
            continue
        if _norm_ws(c) in _EXEMPT_SUBSTRINGS:
            return True
        if _norm_ws(c) in blob_cf:
            return True
    return False


def validate_critique_motivations(
    critique: dict[str, Any],
    *,
    rules_text: str,
    domain_notes: str | None = None,
) -> list[str]:
    """
    Return human-readable errors for hallucinated ``motivating_rule_text`` values.
    Pre-refiner gate (Sig_Agents README / signature_critic Cursor notes).
    """
    blob = _blob_casefold(rules_text, domain_notes)
    errors: list[str] = []
    for section, key in _MOTIVATION_SECTION_KEYS.items():
        items = critique.get(section)
        if not isinstance(items, list):
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            mot = item.get(key)
            if mot is None:
                errors.append(f"{section}[{i}]: missing {key!r} (required for validation)")
                continue
            if not isinstance(mot, str):
                errors.append(f"{section}[{i}]: {key} must be a string")
                continue
            if not _motivation_satisfied(mot, blob):
                errors.append(
                    f"{section}[{i}]: {key!r} does not appear to be grounded in rules/domain_notes: "
                    f"{mot[:120]!r}"
                )
    return errors
