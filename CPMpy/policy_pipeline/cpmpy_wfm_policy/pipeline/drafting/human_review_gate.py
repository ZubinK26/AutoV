"""Human review checkpoints + workflow_state.json (workflow §5.4, §6.7)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class WorkflowState:
    phase_0a_approved: bool = False
    phase_0b_approved: bool = False
    updated_at: str = ""
    notes: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_jsonable(cls, d: dict[str, Any]) -> WorkflowState:
        return cls(
            phase_0a_approved=bool(d.get("phase_0a_approved", False)),
            phase_0b_approved=bool(d.get("phase_0b_approved", False)),
            updated_at=str(d.get("updated_at", "")),
            notes=str(d.get("notes", "")),
            meta=dict(d.get("meta") or {}),
        )


def default_workflow_state_path(domain_dir: Path) -> Path:
    return Path(domain_dir).resolve() / "workflow_state.json"


def load_workflow_state(domain_dir: Path, path: Path | None = None) -> WorkflowState:
    p = path or default_workflow_state_path(domain_dir)
    if not p.is_file():
        return WorkflowState()
    return WorkflowState.from_jsonable(json.loads(p.read_text(encoding="utf-8")))


def save_workflow_state(
    domain_dir: Path,
    state: WorkflowState,
    path: Path | None = None,
) -> None:
    p = path or default_workflow_state_path(domain_dir)
    state.updated_at = datetime.now(timezone.utc).isoformat()
    p.write_text(json.dumps(state.to_jsonable(), indent=2), encoding="utf-8")


def record_human_review_diff(
    *,
    out_path: Path,
    phase: str,
    edited_files: list[str],
    unified_diff: str | None = None,
) -> None:
    rec = {
        "phase": phase,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "edited_files": edited_files,
        "unified_diff": unified_diff,
    }
    out_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
