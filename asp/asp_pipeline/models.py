"""Bundle record and pipeline result models for the ASP path."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

PipelineStatus = Literal["success", "failed"]


@dataclass
class AspPipelineRunResult:
    bundle_id: str
    policy_model_path: str
    bundle_record_path: str
    log_path: str
    status: PipelineStatus
    failure_reason: Optional[str]
    rule_ids: list[str]


@dataclass
class AspFormalizerContext:
    bundle_id: str
    policy_path: str
    policy_text: str
    existing_rule_count: int
    in_scope_lines: list[str]
    attempt_index: int
    """Optional: parse, grounding, or semantic (critic) feedback to fold into the user message."""
    feedback: Optional[str] = None
    previous_lp_block: Optional[str] = None


@dataclass
class AspCriticContext:
    bundle_id: str
    proposed_lp_block: str
    policy_path: str
    policy_text: str
    in_scope_wfm_summary: str = ""


@dataclass
class LogEvent:
    ts: str
    event: str
    data: dict[str, Any] = field(default_factory=dict)
