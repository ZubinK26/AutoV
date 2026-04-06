"""Load handoff bundles and registry shells from JSON (`registry_persistence_v1.md`)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from registry_stage.models import (
    SCHEMA_VERSION,
    AGENT3_VERDICTS,
    ENTRY_KINDS,
    ENTRY_STATUS,
    HandoffBundle,
    HandoffLine,
    RegistryEntry,
    RegistryFile,
)


def load_handoff_bundle(path: str | Path) -> HandoffBundle:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return parse_handoff_bundle(data)


def load_registry(path: str | Path) -> RegistryFile:
    p = Path(path)
    if not p.is_file():
        return RegistryFile(
            schema_version=SCHEMA_VERSION,
            entries=[],
            entry_edges=[],
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    return parse_registry_file(data)


def parse_handoff_bundle(data: Any) -> HandoffBundle:
    if not isinstance(data, dict):
        raise ValueError("handoff root must be a JSON object")

    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise ValueError(f"unsupported handoff schema_version: {sv!r} (expected {SCHEMA_VERSION!r})")

    bundle_id = data.get("bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise ValueError("bundle_id must be a non-empty string")

    user_original_input = data.get("user_original_input")
    if not isinstance(user_original_input, str):
        raise ValueError("user_original_input must be a string")

    raw_lines = data.get("lines")
    if not isinstance(raw_lines, list) or len(raw_lines) == 0:
        raise ValueError("lines must be a non-empty list")

    lines = [_parse_handoff_line(ln, i) for i, ln in enumerate(raw_lines)]

    wfm_ts = data.get("wfm_pipeline_timestamps")
    if wfm_ts is None:
        wfm_ts = {}
    if not isinstance(wfm_ts, dict):
        raise ValueError("wfm_pipeline_timestamps must be an object when present")

    wcl = data.get("wfm_compound_operator_limit")
    if wcl is not None and not isinstance(wcl, int):
        raise ValueError("wfm_compound_operator_limit must be an integer when present")

    return HandoffBundle(
        schema_version=sv,
        bundle_id=bundle_id,
        user_original_input=user_original_input,
        lines=lines,
        confirmation_package_style_a=_optional_str(data.get("confirmation_package_style_a")),
        orchestration_run_id=_optional_str(data.get("orchestration_run_id")),
        wfm_pipeline_timestamps=dict(wfm_ts),
        provider_model=_optional_str(data.get("provider_model")),
        wfm_compound_operator_limit=wcl,
    )


def _optional_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    raise ValueError("expected string or null")


def _parse_handoff_line(obj: Any, index: int) -> HandoffLine:
    if not isinstance(obj, dict):
        raise ValueError(f"lines[{index}] must be a JSON object")

    li = obj.get("line_index")
    if not isinstance(li, int):
        raise ValueError(f"lines[{index}].line_index must be an integer")

    st = obj.get("statement_nl")
    if not isinstance(st, str):
        raise ValueError(f"lines[{index}].statement_nl must be a string")

    verdict = obj.get("agent3_verdict")
    if verdict not in AGENT3_VERDICTS:
        raise ValueError(
            f"lines[{index}].agent3_verdict must be one of {sorted(AGENT3_VERDICTS)}, got {verdict!r}"
        )

    return HandoffLine(
        line_index=li,
        statement_nl=st,
        agent3_verdict=verdict,
        scope_report=_optional_str(obj.get("scope_report")),
        diff_report=_optional_str(obj.get("diff_report")),
        agent2_line_text=_optional_str(obj.get("agent2_line_text")),
    )


def parse_registry_file(data: Any) -> RegistryFile:
    if not isinstance(data, dict):
        raise ValueError("registry root must be a JSON object")

    sv = data.get("schema_version", SCHEMA_VERSION)
    if sv != SCHEMA_VERSION:
        raise ValueError(f"unsupported registry schema_version: {sv!r} (expected {SCHEMA_VERSION!r})")

    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        raise ValueError("entries must be a list")

    edges = data.get("entry_edges")
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        raise ValueError("entry_edges must be a list")

    for j, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"entry_edges[{j}] must be a JSON object")

    entries = [_parse_registry_entry(e, i) for i, e in enumerate(raw_entries)]

    return RegistryFile(
        schema_version=sv,
        entries=entries,
        entry_edges=[dict(e) for e in edges],
    )


def _parse_registry_entry(obj: Any, index: int) -> RegistryEntry:
    if not isinstance(obj, dict):
        raise ValueError(f"entries[{index}] must be a JSON object")

    eid = obj.get("id")
    if not isinstance(eid, str) or not eid:
        raise ValueError(f"entries[{index}].id must be a non-empty string")

    kind = obj.get("kind")
    if kind not in ENTRY_KINDS:
        raise ValueError(f"entries[{index}].kind must be one of {sorted(ENTRY_KINDS)}, got {kind!r}")

    name = obj.get("name")
    if not isinstance(name, str):
        raise ValueError(f"entries[{index}].name must be a string")

    source_rule = obj.get("source_rule", [])
    if not isinstance(source_rule, list) or not all(isinstance(x, str) for x in source_rule):
        raise ValueError(f"entries[{index}].source_rule must be a list of strings")

    nl_description = obj.get("nl_description", "")
    if not isinstance(nl_description, str):
        raise ValueError(f"entries[{index}].nl_description must be a string")

    status = obj.get("status", "active")
    if status not in ENTRY_STATUS:
        raise ValueError(f"entries[{index}].status must be one of {sorted(ENTRY_STATUS)}, got {status!r}")

    members = obj.get("members")
    if members is not None:
        if not isinstance(members, list) or not all(isinstance(x, str) for x in members):
            raise ValueError(f"entries[{index}].members must be a list of strings or omitted")

    parent_sort_id = obj.get("parent_sort_id")
    if parent_sort_id is not None and not isinstance(parent_sort_id, str):
        raise ValueError(f"entries[{index}].parent_sort_id must be a string or omitted")

    domain_sort_ids = obj.get("domain_sort_ids")
    if domain_sort_ids is not None:
        if not isinstance(domain_sort_ids, list) or not all(isinstance(x, str) for x in domain_sort_ids):
            raise ValueError(f"entries[{index}].domain_sort_ids must be a list of strings or omitted")

    codomain_sort_id = obj.get("codomain_sort_id")
    if codomain_sort_id is not None and not isinstance(codomain_sort_id, str):
        raise ValueError(f"entries[{index}].codomain_sort_id must be a string or omitted")

    embedding = obj.get("embedding")
    if embedding is not None:
        if not isinstance(embedding, list) or not all(isinstance(x, (int, float)) for x in embedding):
            raise ValueError(f"entries[{index}].embedding must be a list of numbers or omitted")

    tombstone_reason = obj.get("tombstone_reason")
    if tombstone_reason is not None and not isinstance(tombstone_reason, str):
        raise ValueError(f"entries[{index}].tombstone_reason must be a string or omitted")

    if kind == "constant":
        if not parent_sort_id:
            raise ValueError(f"entries[{index}] kind constant requires parent_sort_id")

    if kind == "function":
        if domain_sort_ids is None or len(domain_sort_ids) == 0:
            raise ValueError(f"entries[{index}] kind function requires non-empty domain_sort_ids")
        if not codomain_sort_id:
            raise ValueError(f"entries[{index}] kind function requires codomain_sort_id")

    return RegistryEntry(
        id=eid,
        kind=kind,
        name=name,
        source_rule=list(source_rule),
        nl_description=nl_description,
        status=status,
        members=list(members) if members is not None else None,
        parent_sort_id=parent_sort_id,
        domain_sort_ids=list(domain_sort_ids) if domain_sort_ids is not None else None,
        codomain_sort_id=codomain_sort_id,
        embedding=list(embedding) if embedding is not None else None,
        tombstone_reason=tombstone_reason,
    )
