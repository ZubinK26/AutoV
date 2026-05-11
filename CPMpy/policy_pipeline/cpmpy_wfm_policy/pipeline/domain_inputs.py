"""Validate domain bundle files (tools.json, … slice 7)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class ToolEntry(BaseModel):
    name: str
    parameters: dict[str, str] = Field(default_factory=dict)
    is_gated: bool = True

    @field_validator("name")
    @classmethod
    def name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("tool name must be non-empty")
        return v.strip()


class ToolsJson(BaseModel):
    tools: list[ToolEntry]


def parse_tools_json(text: str) -> ToolsJson:
    return ToolsJson.model_validate(json.loads(text))


def load_tools_json_file(path: str | Path) -> ToolsJson:
    p = Path(path)
    return parse_tools_json(p.read_text(encoding="utf-8"))


def gated_tool_names(tools: ToolsJson) -> list[str]:
    return [t.name for t in tools.tools if t.is_gated]


def validate_domain_dir_layout(domain_dir: Path) -> list[str]:
    """Return human-readable problems; empty means layout OK for orchestrator."""
    errs: list[str] = []
    d = domain_dir.resolve()
    for name in ("signature.py", "glossary.md", "rules.txt", "tools.json"):
        if not (d / name).is_file():
            errs.append(f"missing {name}")
    return errs


def load_tool_dependencies_from_signature(signature_path: str | Path) -> dict[str, list[str]]:
    """Read ``TOOL_DEPENDENCIES`` from an on-disk signature module (best-effort)."""
    import importlib.util

    p = Path(signature_path).resolve()
    spec = importlib.util.spec_from_file_location("_sig_validate", p)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw = getattr(mod, "TOOL_DEPENDENCIES", None)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError("TOOL_DEPENDENCIES must be a dict")
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if isinstance(v, (list, tuple)):
            out[str(k)] = [str(x) for x in v]
        else:
            raise TypeError(f"TOOL_DEPENDENCIES[{k!r}] must be a list")
    return out
