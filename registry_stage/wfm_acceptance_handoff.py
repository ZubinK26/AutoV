"""
G1 — Build ``HandoffBundle`` from structured WFM acceptance state (no Markdown parsing).

See ``development_plan_g1_g2_orchestration.md``. Orchestration should populate
``WfmAcceptanceSnapshot`` in-process, then call :func:`build_handoff_bundle` and
optionally :func:`write_handoff_bundle` before ``run_bundle_through_registry``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from registry_stage.loaders import parse_handoff_bundle
from registry_stage.models import (
    AGENT3_VERDICTS,
    SCHEMA_VERSION,
    HandoffBundle,
    HandoffLine,
    handoff_bundle_to_dict,
)


@dataclass(frozen=True)
class WfmAcceptanceLine:
    """One confirmation line after Agent 3, aligned with ``HandoffLine`` (0-based ``line_index``)."""

    line_index: int
    statement_nl: str
    agent3_verdict: str
    scope_report: str | None = None
    diff_report: str | None = None
    agent2_line_text: str | None = None

    def __post_init__(self) -> None:
        if self.agent3_verdict not in AGENT3_VERDICTS:
            raise ValueError(
                f"agent3_verdict must be one of {sorted(AGENT3_VERDICTS)}, got {self.agent3_verdict!r}"
            )
        if self.line_index < 0:
            raise ValueError("line_index must be non-negative")


@dataclass
class WfmAcceptanceSnapshot:
    """Structured state at “proceed to registry” time (filled by orchestrator, not by hand-typing JSON at runtime)."""

    bundle_id: str
    user_original_input: str
    lines: tuple[WfmAcceptanceLine, ...]
    confirmation_package_style_a: str | None = None
    orchestration_run_id: str | None = None
    wfm_pipeline_timestamps: dict[str, Any] = field(default_factory=dict)
    provider_model: str | None = None
    wfm_compound_operator_limit: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.bundle_id, str) or not self.bundle_id.strip():
            raise ValueError("bundle_id must be a non-empty string")
        if not isinstance(self.user_original_input, str):
            raise ValueError("user_original_input must be a string")
        if len(self.lines) == 0:
            raise ValueError("lines must be non-empty")
        seen: set[int] = set()
        for ln in self.lines:
            if ln.line_index in seen:
                raise ValueError(f"duplicate line_index: {ln.line_index}")
            seen.add(ln.line_index)


def build_handoff_bundle(snapshot: WfmAcceptanceSnapshot) -> HandoffBundle:
    """Map acceptance snapshot to ``HandoffBundle`` (registry handoff schema)."""
    hl = [
        HandoffLine(
            line_index=ln.line_index,
            statement_nl=ln.statement_nl,
            agent3_verdict=ln.agent3_verdict,
            scope_report=ln.scope_report,
            diff_report=ln.diff_report,
            agent2_line_text=ln.agent2_line_text,
        )
        for ln in sorted(snapshot.lines, key=lambda x: x.line_index)
    ]
    return HandoffBundle(
        schema_version=SCHEMA_VERSION,
        bundle_id=snapshot.bundle_id.strip(),
        user_original_input=snapshot.user_original_input,
        lines=hl,
        confirmation_package_style_a=snapshot.confirmation_package_style_a,
        orchestration_run_id=snapshot.orchestration_run_id,
        wfm_pipeline_timestamps=dict(snapshot.wfm_pipeline_timestamps),
        provider_model=snapshot.provider_model,
        wfm_compound_operator_limit=snapshot.wfm_compound_operator_limit,
    )


def validate_handoff_roundtrip(bundle: HandoffBundle) -> HandoffBundle:
    """
    Ensure the bundle round-trips through ``handoff_bundle_to_dict`` → ``parse_handoff_bundle``
    (same validation as ``load_handoff_bundle`` on disk).
    """
    raw = json.loads(json.dumps(handoff_bundle_to_dict(bundle)))
    return parse_handoff_bundle(raw)


def write_handoff_bundle(path: str | Path, bundle: HandoffBundle, **json_dumps_kw: Any) -> None:
    """Write ``bundles/{bundle_id}.json``-compatible JSON."""
    p = Path(path)
    payload = handoff_bundle_to_dict(bundle)
    kwargs: dict[str, Any] = {"indent": 2, "ensure_ascii": False}
    kwargs.update(json_dumps_kw)
    p.write_text(json.dumps(payload, **kwargs) + "\n", encoding="utf-8")


def acceptance_snapshot_from_jsonable(data: dict[str, Any]) -> WfmAcceptanceSnapshot:
    """
    Load :class:`WfmAcceptanceSnapshot` from a JSON object (e.g. checked-in acceptance snapshot for tests).

    Keys: ``bundle_id``, ``user_original_input``, ``lines`` (list of objects with
    ``line_index``, ``statement_nl``, ``agent3_verdict``, optional ``scope_report``,
    ``diff_report``, ``agent2_line_text``). Optional: ``confirmation_package_style_a``,
    ``orchestration_run_id``, ``wfm_pipeline_timestamps``, ``provider_model``,
    ``wfm_compound_operator_limit``.

    If ``schema_version`` is present (e.g. full handoff JSON), it is **ignored** here —
    the snapshot describes acceptance data only; :func:`build_handoff_bundle` sets schema.
    """
    if not isinstance(data, dict):
        raise ValueError("root must be a JSON object")

    data = dict(data)
    data.pop("schema_version", None)

    raw_lines = data.get("lines")
    if not isinstance(raw_lines, list) or not raw_lines:
        raise ValueError("lines must be a non-empty list")

    lines: list[WfmAcceptanceLine] = []
    for i, obj in enumerate(raw_lines):
        if not isinstance(obj, dict):
            raise ValueError(f"lines[{i}] must be an object")
        li = obj.get("line_index")
        if not isinstance(li, int):
            raise ValueError(f"lines[{i}].line_index must be an integer")
        st = obj.get("statement_nl")
        if not isinstance(st, str):
            raise ValueError(f"lines[{i}].statement_nl must be a string")
        v = obj.get("agent3_verdict")
        if not isinstance(v, str):
            raise ValueError(f"lines[{i}].agent3_verdict must be a string")
        lines.append(
            WfmAcceptanceLine(
                line_index=li,
                statement_nl=st,
                agent3_verdict=v,
                scope_report=_opt_str(obj.get("scope_report")),
                diff_report=_opt_str(obj.get("diff_report")),
                agent2_line_text=_opt_str(obj.get("agent2_line_text")),
            )
        )

    wfm_ts = data.get("wfm_pipeline_timestamps")
    if wfm_ts is None:
        wfm_ts = {}
    if not isinstance(wfm_ts, dict):
        raise ValueError("wfm_pipeline_timestamps must be an object when present")

    wcl = data.get("wfm_compound_operator_limit")
    if wcl is not None and not isinstance(wcl, int):
        raise ValueError("wfm_compound_operator_limit must be an integer when present")

    bid = data.get("bundle_id")
    if not isinstance(bid, str) or not bid:
        raise ValueError("bundle_id must be a non-empty string")

    uoi = data.get("user_original_input")
    if not isinstance(uoi, str):
        raise ValueError("user_original_input must be a string")

    return WfmAcceptanceSnapshot(
        bundle_id=bid,
        user_original_input=uoi,
        lines=tuple(lines),
        confirmation_package_style_a=_opt_str(data.get("confirmation_package_style_a")),
        orchestration_run_id=_opt_str(data.get("orchestration_run_id")),
        wfm_pipeline_timestamps=dict(wfm_ts),
        provider_model=_opt_str(data.get("provider_model")),
        wfm_compound_operator_limit=wcl,
    )


def load_acceptance_snapshot(path: str | Path) -> WfmAcceptanceSnapshot:
    """Load :class:`WfmAcceptanceSnapshot` from a UTF-8 JSON file."""
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    return acceptance_snapshot_from_jsonable(data)


def _opt_str(v: Any) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        return v
    raise ValueError("expected string or null")
