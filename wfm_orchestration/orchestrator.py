"""
WFM → registry e2e: Agents 1–3, confirmation, optional Agent 4 + Style-A re-entry, then handoff.

Implements **G2** (same-process loop) and completes **G1** wiring (``WfmAcceptanceSnapshot`` → registry).
See ``development_plan_g1_g2_orchestration.md``.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TextIO

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO / "test_sets" / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "test_sets" / "scripts"))

import wfm_agent4_common as w4  # noqa: E402

from registry_stage.bundle_workflow import run_bundle_through_registry
from registry_stage.export_session import export_session
from registry_stage.view_dev_session import write_dev_session_views
from registry_stage.line_driver import LineDriverConfig
from registry_stage.models import DevSessionSnapshot
from registry_stage.registry_session import RegistrySession
from registry_stage.wfm_acceptance_handoff import (
    build_handoff_bundle,
    validate_handoff_roundtrip,
    write_handoff_bundle,
)

from wfm_orchestration.agent4_call import call_agent4_gemini
from wfm_orchestration.gemini_client import call_gemini, env_thinking_level
from wfm_orchestration.prompts_wfm import load_wfm_prompts
from wfm_orchestration.snapshot_from_agents import wfm_acceptance_snapshot_from_agent_outputs
from wfm_orchestration.run_metadata import (
    new_bundle_id,
    orchestration_run_id_accept,
    wfm_pipeline_timestamps_at_accept,
)
from wfm_orchestration.style_a_merge import style_a_merged_nl

OUTER_PASSES_MAX = 4


def _write_e2e_auto_artifacts(
    dev: DevSessionSnapshot,
    *,
    repo_root: Path,
    print_fn: Callable[..., None],
    stderr: TextIO,
) -> None:
    """Timestamped folder under ``exports/e2e_demo_runs/`` — JSON + G8 Markdown viewer."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = uuid.uuid4().hex[:8]
    base = repo_root / "exports" / "e2e_demo_runs" / f"{ts}_{run_id}"
    base.mkdir(parents=True, exist_ok=True)
    json_path = base / "dev_session.json"
    viewer_dir = base / "viewer"
    try:
        export_session(json_path, dev)
        write_dev_session_views(dev.to_jsonable(), viewer_dir)
    except Exception as e:
        stderr.write(f"[e2e artifacts] failed: {e}\n")
        return
    print_fn(f"\n[e2e artifacts] Run folder: {base}")
    print_fn(f"  Dev session JSON: {json_path}")
    print_fn(f"  Readable viewer (start here): {viewer_dir / 'index.md'}")


def _parse_int_list(s: str) -> list[int]:
    s = s.strip()
    if not s:
        return []
    out: list[int] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(int(part))
    return out


def run_wfm_registry_e2e(
    *,
    initial_user_text: str,
    client: Any,
    model: str,
    temperature: float,
    max_output_tokens: int,
    thinking_level: Any,
    registry_session: RegistrySession,
    llm_complete: Callable[[str, str], str],
    bundle_id: str | None = None,
    bundle_id_prefix: str = "demo",
    provider_model: str | None = None,
    export_json: Path | None = None,
    handoff_json: Path | None = None,
    auto_artifacts: bool = True,
    input_fn: Callable[[str], str] = input,
    print_fn: Callable[..., None] = print,
    stderr: TextIO = sys.stderr,
) -> DevSessionSnapshot | None:
    """
    Interactive console session: WFM loop(s) then registry when user accepts.

    **Environment:** ``GEMINI_API_KEY`` required. Run from repo root so ``registry_stage`` imports work.
    """
    p1, p2, p3, p4, compound_limit = load_wfm_prompts()
    bid = bundle_id or new_bundle_id(prefix=bundle_id_prefix)
    user_original_input = initial_user_text
    user_nl = initial_user_text

    for pass_ix in range(OUTER_PASSES_MAX):
        print_fn(f"\n--- WFM pass {pass_ix + 1}/{OUTER_PASSES_MAX} ---\n")
        if pass_ix > 0:
            print_fn(
                "[Orchestration] Re-running full WFM from Agent 1 on the merged Style-A rule "
                "(no separate CLI run).\n"
            )

        a1_text, _u1 = call_gemini(
            client,
            model=model,
            system=p1,
            user=user_nl,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
        )
        a2_text, _u2 = call_gemini(
            client,
            model=model,
            system=p2,
            user=a1_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
        )
        if w4.limit_exceeded(a2_text):
            stderr.write("Agent 2 LIMIT_EXCEEDED — WFM stops (per Agent_WFM).\n")
            return None

        a3_text, _u3 = call_gemini(
            client,
            model=model,
            system=p3,
            user=a2_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
        )

        print_fn("### Agent 2 (decomposition)\n")
        print_fn(a2_text)
        print_fn("\n### Agent 3 (scope / rewrite)\n")
        print_fn(a3_text)
        print_fn("")

        ans = input_fn("Accept entire confirmation package for registry handoff? [Y/n]: ").strip().lower()
        if ans in ("", "y", "yes"):
            ts_dict = wfm_pipeline_timestamps_at_accept()
            snap = wfm_acceptance_snapshot_from_agent_outputs(
                bundle_id=bid,
                user_original_input=user_original_input,
                agent2_output=a2_text,
                agent3_output=a3_text,
                confirmation_package_style_a=None,
                orchestration_run_id=orchestration_run_id_accept(
                    bundle_id=bid, outer_pass_index=pass_ix
                ),
                wfm_pipeline_timestamps=ts_dict,
                provider_model=provider_model or model,
                wfm_compound_operator_limit=compound_limit,
            )
            bundle = validate_handoff_roundtrip(build_handoff_bundle(snap))
            if handoff_json is not None:
                write_handoff_bundle(handoff_json, bundle)
                print_fn(f"Wrote handoff: {handoff_json}")
            cfg = LineDriverConfig(enable_llm=True, llm_complete=llm_complete)
            dev = run_bundle_through_registry(
                bundle,
                registry_session,
                llm_complete=llm_complete,
                line_config=cfg,
            )
            if export_json is not None:
                export_session(export_json, dev)
                print_fn(f"Wrote dev export: {export_json}")
            if auto_artifacts:
                _write_e2e_auto_artifacts(dev, repo_root=_REPO, print_fn=print_fn, stderr=stderr)
            return dev

        raw_d = input_fn(
            "1-based line indices to disagree (comma-separated), or 'abort' to stop: "
        ).strip()
        if raw_d.lower() == "abort":
            print_fn("Aborted.")
            return None
        disagree = _parse_int_list(raw_d)
        if not disagree:
            stderr.write("No disagreed lines — type 'abort' or provide at least one index.\n")
            return None

        comments: list[str] = []
        for d in disagree:
            c = input_fn(f"Comment for line {d} (non-empty): ").strip()
            if not c:
                stderr.write("Empty comment — abort.\n")
                return None
            comments.append(c)

        raw_o = input_fn(
            "1-based OUT_OF_SCOPE line indices to **confirm omit** (comma-separated), or empty: "
        ).strip()
        omit_confirmed = _parse_int_list(raw_o)

        row: dict[str, Any] = {
            "example_id": bid,
            "difficulty": "wfm_registry_e2e",
            "agent_2": {"output": a2_text},
            "agent_3": {"output": a3_text},
        }
        payload = w4.build_user_payload(
            row=row,
            run_path=Path("inline_e2e"),
            disagree=disagree,
            comments=comments,
            omit_confirmed=omit_confirmed,
        )
        print_fn("\n--- Calling Agent 4 ---\n")
        a4_text = call_agent4_gemini(payload, system=p4)
        print_fn(a4_text)
        print_fn("")

        try:
            merged = style_a_merged_nl(
                a4_text,
                agent2_output=a2_text,
                agent3_output=a3_text,
                disagree_1based=disagree,
                omit_confirmed_1based=omit_confirmed,
            )
        except ValueError as e:
            stderr.write(f"Merge failed: {e}\n")
            return None

        print_fn(
            "[Orchestration] Merged Style-A rule will be sent to Agent 1 next (automatic).\n"
        )
        user_nl = merged

    stderr.write("Outer WFM rerun budget exhausted (4 passes).\n")
    return None
