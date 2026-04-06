"""Typed structures for `registry_persistence_v1.md` handoff and registry shell."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = "registry_persistence_v1"

AGENT3_VERDICTS = frozenset({"PASS", "REWRITE", "OUT_OF_SCOPE"})
ENTRY_KINDS = frozenset({"sort", "constant", "function"})
ENTRY_STATUS = frozenset({"active", "tombstoned"})


@dataclass(frozen=True)
class StructuredGap:
    """LLM gap payload for M3+ (M4 resolve / M5 populate consume `surface`, `kind`, hints)."""

    surface: str
    kind: str
    arity_hint: int | None = None
    domain_hints: tuple[str, ...] = ()
    notes: str = ""


@dataclass
class HandoffLine:
    line_index: int
    statement_nl: str
    agent3_verdict: str
    scope_report: str | None = None
    diff_report: str | None = None
    agent2_line_text: str | None = None


@dataclass
class HandoffBundle:
    schema_version: str
    bundle_id: str
    user_original_input: str
    lines: list[HandoffLine]
    confirmation_package_style_a: str | None = None
    orchestration_run_id: str | None = None
    wfm_pipeline_timestamps: dict[str, Any] = field(default_factory=dict)
    provider_model: str | None = None
    wfm_compound_operator_limit: int | None = None


@dataclass
class RegistryEntry:
    id: str
    kind: str
    name: str
    source_rule: list[str] = field(default_factory=list)
    nl_description: str = ""
    status: str = "active"
    members: list[str] | None = None
    parent_sort_id: str | None = None
    domain_sort_ids: list[str] | None = None
    codomain_sort_id: str | None = None
    embedding: list[float] | None = None
    tombstone_reason: str | None = None


@dataclass
class RegistryFile:
    schema_version: str
    entries: list[RegistryEntry]
    entry_edges: list[dict[str, Any]]


@dataclass
class DevSessionSnapshot:
    """
    Dev-only export (not a production `registry.json` / commit).
    See `development_plan_registry_stage_v1.md` M1.
    """

    registry: RegistryFile | None = None
    bundle: HandoffBundle | None = None
    line_traces: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""

    def to_jsonable(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "dev_export": True,
            "notes": self.notes,
            "line_traces": list(self.line_traces),
        }
        if self.bundle is not None:
            out["bundle_id"] = self.bundle.bundle_id
            out["handoff"] = handoff_bundle_to_dict(self.bundle)
        else:
            out["bundle_id"] = None
            out["handoff"] = None
        out["registry"] = (
            registry_file_to_dict(self.registry)
            if self.registry is not None
            else empty_registry_dict()
        )
        return out


def empty_registry_dict() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "entries": [],
        "entry_edges": [],
    }


def handoff_bundle_to_dict(bundle: HandoffBundle) -> dict[str, Any]:
    d: dict[str, Any] = {
        "schema_version": bundle.schema_version,
        "bundle_id": bundle.bundle_id,
        "user_original_input": bundle.user_original_input,
        "lines": [asdict(ln) for ln in bundle.lines],
    }
    if bundle.confirmation_package_style_a is not None:
        d["confirmation_package_style_a"] = bundle.confirmation_package_style_a
    if bundle.orchestration_run_id is not None:
        d["orchestration_run_id"] = bundle.orchestration_run_id
    if bundle.wfm_pipeline_timestamps:
        d["wfm_pipeline_timestamps"] = dict(bundle.wfm_pipeline_timestamps)
    if bundle.provider_model is not None:
        d["provider_model"] = bundle.provider_model
    if bundle.wfm_compound_operator_limit is not None:
        d["wfm_compound_operator_limit"] = bundle.wfm_compound_operator_limit
    return d


def registry_entry_to_dict(entry: RegistryEntry) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": entry.id,
        "kind": entry.kind,
        "name": entry.name,
        "source_rule": list(entry.source_rule),
        "nl_description": entry.nl_description,
        "status": entry.status,
    }
    if entry.members is not None:
        d["members"] = list(entry.members)
    if entry.parent_sort_id is not None:
        d["parent_sort_id"] = entry.parent_sort_id
    if entry.domain_sort_ids is not None:
        d["domain_sort_ids"] = list(entry.domain_sort_ids)
    if entry.codomain_sort_id is not None:
        d["codomain_sort_id"] = entry.codomain_sort_id
    if entry.embedding is not None:
        d["embedding"] = list(entry.embedding)
    if entry.tombstone_reason is not None:
        d["tombstone_reason"] = entry.tombstone_reason
    return d


def registry_file_to_dict(reg: RegistryFile) -> dict[str, Any]:
    return {
        "schema_version": reg.schema_version,
        "entries": [registry_entry_to_dict(e) for e in reg.entries],
        "entry_edges": list(reg.entry_edges),
    }
