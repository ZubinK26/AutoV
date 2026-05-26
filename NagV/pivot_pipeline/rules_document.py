"""Parse and validate ``rules_extracted.json`` envelopes (version + vNext extensions)."""

from __future__ import annotations

from typing import Any

from pivot_pipeline.constants import (
    PIVOT_IR_EXTENSIONS_MANIFEST,
    POLICY_SEMANTICS_VERSION_DEFAULT,
    POLICY_SEMANTICS_VERSION_VNEXT,
)
from pivot_pipeline.ir_vnext import VNEXT_TEMPLATE_CLASSES


def rules_contain_vnext_templates(rules: list[dict[str, Any]]) -> bool:
    return any(str(r.get("template_class")) in VNEXT_TEMPLATE_CLASSES for r in rules)


def parse_rules_document(body: dict[str, Any]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    """
    Validate rules file envelope and return ``(policy_id, rules, envelope_meta)``.

    ``envelope_meta`` may include ``policy_semantics_version`` and ``pivot_ir_extensions``.
    """
    if not isinstance(body, dict):
        raise ValueError("rules document must be a JSON object")
    policy_id = body.get("policy_id")
    rules = body.get("rules")
    if not policy_id or not isinstance(rules, list):
        raise ValueError("rules document requires policy_id and rules array")

    version = str(body.get("policy_semantics_version") or POLICY_SEMANTICS_VERSION_DEFAULT)
    raw_ext = body.get("pivot_ir_extensions")
    extensions: list[str] = []
    if raw_ext is not None:
        if not isinstance(raw_ext, list) or not all(isinstance(x, str) for x in raw_ext):
            raise ValueError("pivot_ir_extensions must be a list of strings")
        extensions = list(raw_ext)

    has_vnext = rules_contain_vnext_templates(rules)
    if has_vnext:
        if version == POLICY_SEMANTICS_VERSION_DEFAULT:
            raise ValueError(
                "rules contain vNext expansion templates but policy_semantics_version is "
                f"{POLICY_SEMANTICS_VERSION_DEFAULT!r}; use {POLICY_SEMANTICS_VERSION_VNEXT!r} with "
                f'pivot_ir_extensions: ["{PIVOT_IR_EXTENSIONS_MANIFEST}"]'
            )
        if PIVOT_IR_EXTENSIONS_MANIFEST not in extensions:
            raise ValueError(
                f"rules contain vNext templates; pivot_ir_extensions must include "
                f"{PIVOT_IR_EXTENSIONS_MANIFEST!r}"
            )

    if version not in (POLICY_SEMANTICS_VERSION_DEFAULT, POLICY_SEMANTICS_VERSION_VNEXT):
        raise ValueError(
            f"unsupported policy_semantics_version {version!r} "
            f"(supported: {POLICY_SEMANTICS_VERSION_DEFAULT!r}, {POLICY_SEMANTICS_VERSION_VNEXT!r})"
        )

    unknown = [e for e in extensions if e != PIVOT_IR_EXTENSIONS_MANIFEST]
    if unknown:
        raise ValueError(f"unknown pivot_ir_extensions: {unknown!r}")

    meta: dict[str, Any] = {"policy_semantics_version": version}
    if extensions:
        meta["pivot_ir_extensions"] = extensions
    if has_vnext:
        meta["vnext_rules_present"] = True
    return str(policy_id), rules, meta


def build_rules_document(
    policy_id: str,
    rules: list[dict[str, Any]],
    *,
    policy_semantics_version: str | None = None,
    pivot_ir_extensions: list[str] | None = None,
) -> dict[str, Any]:
    """Build a rules_extracted.json payload with correct version/extensions for vNext."""
    has_vnext = rules_contain_vnext_templates(rules)
    version = policy_semantics_version
    if version is None:
        version = POLICY_SEMANTICS_VERSION_VNEXT if has_vnext else POLICY_SEMANTICS_VERSION_DEFAULT
    ext = list(pivot_ir_extensions or [])
    if has_vnext and PIVOT_IR_EXTENSIONS_MANIFEST not in ext:
        ext.append(PIVOT_IR_EXTENSIONS_MANIFEST)
    out: dict[str, Any] = {
        "policy_id": policy_id,
        "policy_semantics_version": version,
        "rules": rules,
    }
    if ext:
        out["pivot_ir_extensions"] = ext
    return out


__all__ = [
    "build_rules_document",
    "parse_rules_document",
    "rules_contain_vnext_templates",
]
