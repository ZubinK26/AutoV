"""Parse and validate ``rules_extracted.json`` envelopes (version + vNext extensions)."""

from __future__ import annotations

import json
from pathlib import Path
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
        # Normalize stripped envelopes (e.g. after test-repair wrote rules-only JSON).
        if version == POLICY_SEMANTICS_VERSION_DEFAULT:
            version = POLICY_SEMANTICS_VERSION_VNEXT
        if PIVOT_IR_EXTENSIONS_MANIFEST not in extensions:
            extensions.append(PIVOT_IR_EXTENSIONS_MANIFEST)

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


def write_rules_document_file(
    path: Path,
    policy_id: str,
    rules: list[dict[str, Any]],
    *,
    rules_envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write ``rules_extracted.json`` (or sibling) with correct vNext envelope metadata."""
    env = rules_envelope or {}
    ext = env.get("pivot_ir_extensions")
    doc = build_rules_document(
        policy_id,
        rules,
        policy_semantics_version=env.get("policy_semantics_version"),
        pivot_ir_extensions=list(ext) if isinstance(ext, list) else None,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return doc


def envelope_from_summary_or_body(
    summary: dict[str, Any] | None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect envelope fields for writes after repair / refresh."""
    out: dict[str, Any] = {}
    for src in (summary, body):
        if not isinstance(src, dict):
            continue
        for key in ("policy_semantics_version", "pivot_ir_extensions"):
            if key in src and key not in out:
                out[key] = src[key]
    return out


__all__ = [
    "build_rules_document",
    "envelope_from_summary_or_body",
    "parse_rules_document",
    "rules_contain_vnext_templates",
    "write_rules_document_file",
]
