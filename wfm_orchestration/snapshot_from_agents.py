"""
Build :class:`registry_stage.wfm_acceptance_handoff.WfmAcceptanceSnapshot` from Agent 2/3 text outputs.

Uses the same parsers as ``test_sets/scripts/wfm_agent4_common.py`` (merge base / effective lines).
Agent 2 indices are **1-based**; ``HandoffLine.line_index`` is **0-based** (``agent2_index - 1``).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO / "test_sets" / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "test_sets" / "scripts"))

import wfm_agent4_common as w4  # noqa: E402

from registry_stage.models import AGENT3_VERDICTS
from registry_stage.wfm_acceptance_handoff import WfmAcceptanceLine, WfmAcceptanceSnapshot


def verdicts_for_indices(agent3_output: str) -> dict[int, str]:
    """Map Agent 2 **1-based** line index -> PASS | REWRITE | OUT_OF_SCOPE (best-effort)."""
    verdicts: dict[int, str] = {}
    line_prefix = r"(?:\d+\.\s+)?"
    num_pat = re.compile(
        rf"^{line_prefix}(PASS|REWRITE|OUT_OF_SCOPE):\s*(\d+)\.\s*"
        r"\"((?:[^\"\\]|\\.)*)\"\s*(?:\|(.*))?\s*$"
    )
    for raw_line in agent3_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = num_pat.match(line)
        if m:
            v = m.group(1)
            idx = int(m.group(2))
            if v in AGENT3_VERDICTS:
                verdicts[idx] = v
    return verdicts


def scope_tail_from_line(agent3_output: str, index: int) -> str | None:
    """If OUT_OF_SCOPE line has ``| reason``, return reason text."""
    line_prefix = r"(?:\d+\.\s+)?"
    num_pat = re.compile(
        rf"^{line_prefix}OUT_OF_SCOPE:\s*{index}\.\s*"
        r"\"((?:[^\"\\]|\\.)*)\"\s*\|\s*(.+?)\s*$"
    )
    for raw_line in agent3_output.splitlines():
        m = num_pat.match(raw_line.strip())
        if m:
            return m.group(2).strip()
    return None


def wfm_acceptance_snapshot_from_agent_outputs(
    *,
    bundle_id: str,
    user_original_input: str,
    agent2_output: str,
    agent3_output: str,
    confirmation_package_style_a: str | None = None,
    orchestration_run_id: str | None = None,
    wfm_pipeline_timestamps: dict[str, Any] | None = None,
    provider_model: str | None = None,
    wfm_compound_operator_limit: int | None = None,
) -> WfmAcceptanceSnapshot:
    """
    Build a snapshot for ``build_handoff_bundle`` after the user **accepts** the confirmation package.

    ``agent2_output`` / ``agent3_output`` must be the same strings used in the WFM run (verbatim).
    """
    effective, _warnings = w4.parse_agent3_effective_lines(agent3_output, agent2_output)
    if not effective:
        raise ValueError("parse_agent3_effective_lines returned no lines — check Agent 2/3 outputs")
    verdicts = verdicts_for_indices(agent3_output)
    base = w4.parse_numbered_lines(agent2_output)
    if not base:
        raise ValueError("Agent 2 had no numbered lines")

    lines: list[WfmAcceptanceLine] = []
    for idx in sorted(effective.keys()):
        v = verdicts.get(idx)
        if v is None:
            v = "PASS"
        if v not in AGENT3_VERDICTS:
            v = "PASS"
        st = effective[idx]
        scope = None
        diff = None
        if v == "OUT_OF_SCOPE":
            scope = scope_tail_from_line(agent3_output, idx)
            if scope is None:
                scope = ""

        a2_line = None
        for raw in agent2_output.splitlines():
            rs = raw.strip()
            if re.match(rf"^{idx}\.\s", rs):
                a2_line = rs
                break

        lines.append(
            WfmAcceptanceLine(
                line_index=idx - 1,
                statement_nl=st,
                agent3_verdict=v,
                scope_report=scope,
                diff_report=diff,
                agent2_line_text=a2_line,
            )
        )

    return WfmAcceptanceSnapshot(
        bundle_id=bundle_id,
        user_original_input=user_original_input,
        lines=tuple(lines),
        confirmation_package_style_a=confirmation_package_style_a,
        orchestration_run_id=orchestration_run_id,
        wfm_pipeline_timestamps=dict(wfm_pipeline_timestamps or {}),
        provider_model=provider_model,
        wfm_compound_operator_limit=wfm_compound_operator_limit,
    )
