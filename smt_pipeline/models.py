"""Bundle record and pipeline result models (`control_flow_v3.md`)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

PipelineStatus = Literal["success", "failed"]


@dataclass
class PolicyBundleRecord:
    bundle_id: str
    committed_at: Optional[str]
    pipeline_status: PipelineStatus
    failure_reason: Optional[str]
    rule_ids: list[str]
    wfm_payload: dict[str, Any]
    policy_model_path: str


@dataclass
class PipelineRunResult:
    bundle_id: str
    policy_model_path: str
    bundle_record_path: str
    log_path: str
    status: PipelineStatus
    failure_reason: Optional[str]
    rule_ids: list[str]


@dataclass
class FormalizerContext:
    bundle_id: str
    policy_path: str
    policy_text: str
    existing_rule_count: int
    in_scope_lines: list[str]
    attempt_index: int
    critic_objections: Optional[str] = None
    previous_smt2_block: Optional[str] = None


@dataclass
class CriticContext:
    bundle_id: str
    proposed_smt2_block: str
    policy_path: str
    policy_text: str
    in_scope_wfm_summary: str = ""


@dataclass
class LogEvent:
    ts: str
    event: str
    data: dict[str, Any] = field(default_factory=dict)
