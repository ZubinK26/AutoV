"""Pydantic schemas for Phase 0 LLM I/O (Sig_Agents + normalization)."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


_CRITIQUE_LIST_KEYS = (
    "missing_fields",
    "surplus_fields",
    "suspicious_bounds",
    "incomplete_enums",
    "naming_violations",
    "helper_concerns",
    "tools_signature_mismatch",
    "cross_section_inconsistencies",
)


class SignatureCritique(BaseModel):
    """Rich critique JSON from `signature_critic.md`; list items are dicts."""

    model_config = ConfigDict(extra="ignore")

    missing_fields: list[dict[str, Any]] = Field(default_factory=list)
    surplus_fields: list[dict[str, Any]] = Field(default_factory=list)
    suspicious_bounds: list[dict[str, Any]] = Field(default_factory=list)
    incomplete_enums: list[dict[str, Any]] = Field(default_factory=list)
    naming_violations: list[dict[str, Any]] = Field(default_factory=list)
    helper_concerns: list[dict[str, Any]] = Field(default_factory=list)
    tools_signature_mismatch: list[dict[str, Any]] = Field(default_factory=list)
    cross_section_inconsistencies: list[dict[str, Any]] = Field(default_factory=list)
    summary_note: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _lists(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data.pop("confidence_per_concern", None)
        for k in _CRITIQUE_LIST_KEYS:
            v = data.get(k)
            if v is None:
                data[k] = []
            elif not isinstance(v, list):
                raise ValueError(f"{k} must be a list, got {type(v).__name__}")
        return data

    def all_findings_enumerated(self) -> list[tuple[str, int, dict[str, Any]]]:
        out: list[tuple[str, int, dict[str, Any]]] = []
        for attr in _CRITIQUE_LIST_KEYS:
            for i, item in enumerate(getattr(self, attr)):
                if isinstance(item, dict):
                    out.append((attr, i, item))
        return out


def critique_finding_count(critique: SignatureCritique) -> int:
    return sum(len(getattr(critique, k)) for k in _CRITIQUE_LIST_KEYS)


class SignatureDrafterOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signature_py: str
    tools_json: dict[str, Any] | None = None
    rationale: dict[str, Any] = Field(default_factory=dict)
    bound_confidence: dict[str, Any] = Field(default_factory=dict)
    enum_completeness: dict[str, Any] = Field(default_factory=dict)
    drafter_notes: str = ""
    co_drafted_tools: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "signature_py_content" in data and "signature_py" not in data:
            data["signature_py"] = data.pop("signature_py_content")
        if "tools_json_content" in data:
            tjc = data.pop("tools_json_content")
            if isinstance(tjc, str):
                tjc = tjc.strip()
                data["tools_json"] = json.loads(tjc) if tjc else None
            elif tjc is None:
                data["tools_json"] = None
        if "signature_rationale" in data and "rationale" not in data:
            data["rationale"] = data.pop("signature_rationale")
        if "rationale" not in data or data["rationale"] is None:
            data["rationale"] = {}
        if "bound_confidence" not in data or data["bound_confidence"] is None:
            data["bound_confidence"] = {}
        if "enum_completeness" not in data or data["enum_completeness"] is None:
            data["enum_completeness"] = {}
        return data

    def rationale_bundle_for_disk(self) -> dict[str, Any]:
        return {
            "rationale": dict(self.rationale),
            "bound_confidence": dict(self.bound_confidence),
            "enum_completeness": dict(self.enum_completeness),
            "drafter_notes": self.drafter_notes,
        }


class SignatureRefinerLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    signature_py: str
    tools_json: dict[str, Any] | None = None
    rationale: dict[str, Any] = Field(default_factory=dict)
    bound_confidence: dict[str, Any] = Field(default_factory=dict)
    enum_completeness: dict[str, Any] = Field(default_factory=dict)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    spontaneous_corrections: list[dict[str, Any]] = Field(default_factory=list)
    refiner_notes: str = ""

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "signature_py_content" in data and "signature_py" not in data:
            data["signature_py"] = data.pop("signature_py_content")
        if "tools_json_content" in data:
            t = data.pop("tools_json_content")
            if isinstance(t, str):
                t = t.strip()
                data["tools_json"] = json.loads(t) if t else None
            else:
                data["tools_json"] = t
        if "refiner_decisions" in data and ("decisions" not in data or data.get("decisions") is None):
            rd = data.pop("refiner_decisions")
            if isinstance(rd, list):
                data["decisions"] = rd
            elif isinstance(rd, dict) and "decisions" in rd:
                data["decisions"] = rd["decisions"]
        if "decisions" not in data or data["decisions"] is None:
            data["decisions"] = []
        if "spontaneous_corrections" not in data or data["spontaneous_corrections"] is None:
            data["spontaneous_corrections"] = []
        return data

    def artifact_for_disk(self) -> dict[str, Any]:
        return {
            "decisions": list(self.decisions),
            "spontaneous_corrections": list(self.spontaneous_corrections),
            "refiner_notes": self.refiner_notes,
            "rationale_updates": dict(self.rationale),
            "bound_confidence_updates": dict(self.bound_confidence),
            "enum_completeness_updates": dict(self.enum_completeness),
        }


class GlossaryDrafterOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    glossary_yaml: str
    drafter_notes: str = ""
    entries_with_inferred_phrases: list[str] = Field(default_factory=list)
    low_confidence_entries: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _yaml_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "glossary_yaml_content" in data and "glossary_yaml" not in data:
            data["glossary_yaml"] = data.pop("glossary_yaml_content")
        return data
