"""Shared interactive semantic critic loop (NL vs synthetic) used after model updates."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.assessment_linearize import expansion_assessment_digest_path
from pivot_pipeline.critic_agent import (
    CriticReport,
    critic_handoff_dict,
    critic_report_passed,
    format_critic_report_terminal,
    run_pivot_critic_parsed,
)
from pivot_pipeline.critic_finding_router import (
    critic_semantic_repair_allow_cross_findings,
    format_routing_summary,
    partition_findings_by_route,
    should_defer_semantic_repair,
)
from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.post_model_workflow import (
    critic_repair_compile_attempts_max,
    critic_repair_max_rounds,
    critic_semantic_repair_max_findings,
)
from pivot_pipeline.semantic_critic_triage import (
    format_critic_triage_summary,
    run_critic_finding_triage,
    write_critic_repair_handoff,
)
from pivot_pipeline.semantic_repair_apply import run_semantic_repair_session
from pivot_pipeline.test_repair_registry import is_repairer_api_error
from pivot_pipeline.varprod_trigger_validate import linearize_varprod_rules_excerpt

BLOCKED_SEMANTIC_REPAIR_COMPILE = "blocked_semantic_repair_compile"


def critic_api_auto_retries_max() -> int | None:
    """
    Max automatic Pivot Critic retries on transient API errors.

    ``PIVOT_CRITIC_API_AUTO_RETRIES=0`` (default) = unlimited in interactive mode.
    """
    raw = os.getenv("PIVOT_CRITIC_API_AUTO_RETRIES", "0").strip()
    if raw in ("", "0"):
        return None
    try:
        return max(1, min(int(raw), 100))
    except ValueError:
        return None


def run_pivot_critic_with_api_retries(
    nl_text: str,
    synth: str,
    *,
    varprod_rules_linearized: str = "",
    expansion_assessment_digest: str = "",
    interactive_any: bool,
    print_fn: Callable[..., None],
) -> tuple[str, CriticReport]:
    """Call Pivot Critic; in interactive mode, retry transient API errors without exiting."""
    attempts = 0
    cap = critic_api_auto_retries_max()
    while True:
        try:
            return run_pivot_critic_parsed(
                nl_text,
                synth,
                varprod_rules_linearized=varprod_rules_linearized,
                expansion_assessment_digest=expansion_assessment_digest,
            )
        except Exception as e:
            if not is_repairer_api_error(e):
                raise
            attempts += 1
            if not interactive_any:
                limit = cap if cap is not None else 3
                if attempts >= limit:
                    raise
            elif cap is not None and attempts > cap:
                raise
            label = f"{attempts}/{cap}" if cap is not None else str(attempts)
            print_fn(
                f"\n[policy gate] Pivot Critic API unavailable ({label}): {e}\n"
                "  Retrying automatically…\n"
            )


def _print_semantic_drift_gate(
    *,
    print_fn: Callable[..., None],
    short: bool,
    compile_attempt_cap: int,
    has_triage: bool,
) -> None:
    if short:
        print_fn(
            f"[policy gate] Semantic repair compile budget exhausted ({compile_attempt_cap} "
            "Repairer_Piv attempts in last REPAIR); policy artifacts unchanged.\n"
            f"  Type {REPAIR_CRITIC_DRIFT_TOKEN!r} to run Repairer_Piv again (same critic report), "
            f"{PROCEED_INCOMPLETE_TOKEN!r} to waive, 'retriage' to re-prompt findings, "
            "or Enter to abort.\n"
            "  No new Pivot Critic call until repair succeeds.\n"
        )
    else:
        print_fn(
            "\n[policy gate] Critic reported DRIFT.\n"
            f"  Type {REPAIR_CRITIC_DRIFT_TOKEN!r} to run Repairer_Piv (semantic) on approved findings, then re-check.\n"
            f"  Type {PROCEED_INCOMPLETE_TOKEN!r} to continue anyway (writes critic_drift_handoff.json).\n"
        )
        if has_triage:
            print_fn("  Type 'retriage' to re-run critic finding triage (y/n).\n")
        print_fn("  Press Enter to abort.\n")


def _handoff_for_semantic_repair(
    report: CriticReport,
    *,
    approved: set[str],
    ignored: set[str],
    work_dir: Path,
    source_note: str,
    **extra: object,
) -> Path:
    approved_findings = [f for f in report.findings if f.id in approved]
    cross, semantic = partition_findings_by_route(approved_findings)
    semantic_ids = {f.id for f in semantic}
    cross_deferred: set[str] = {f.id for f in cross}
    if critic_semantic_repair_allow_cross_findings():
        semantic_ids = set(approved)
        cross_deferred = set()
    elif not semantic_ids:
        semantic_ids = set(approved)
    stub_report = report.model_copy(
        update={"findings": [f for f in report.findings if f.id in semantic_ids]}
    )
    return write_critic_repair_handoff(
        work_dir,
        stub_report,
        approved=semantic_ids,
        ignored=ignored | cross_deferred,
        source_note=source_note,
        **extra,
    )


def run_semantic_critic_interactive_loop(
    *,
    work_dir: Path,
    nl_text_for_artifacts: str,
    nl_for_precheck: Path,
    nl_lines_reg: list[str],
    policy_id: str,
    rules: list[dict[str, Any]],
    meta_path: Path,
    skip_registry: bool,
    no_llm: bool,
    interactive_any: bool,
    with_cross_repair: bool = False,
    print_fn: Callable[..., None],
    input_fn: Callable[[str], str],
    summary: dict[str, Any],
    synth: str,
    meta: Any,
    z3_result: dict[str, Any],
    ok: bool,
    issues: list[Any],
) -> tuple[
    list[dict[str, Any]],
    Any,
    str,
    dict[str, Any],
    bool,
    list[Any],
    str | None,
]:
    """
    Run pivot semantic critic until PASS, waived drift, or block.

    Updates rules/meta/synth/z3/precheck artifacts on semantic REPAIR.
    """
    repair_sessions_used = 0
    compile_attempt_cap = critic_repair_compile_attempts_max()
    short_gate = False
    sticky_approved: set[str] | None = None
    sticky_ignored: set[str] | None = None
    skip_triage_once = False

    while True:
        digest_path = expansion_assessment_digest_path(work_dir)
        expansion_digest = (
            digest_path.read_text(encoding="utf-8") if digest_path.is_file() else ""
        )
        crit_raw, report = run_pivot_critic_with_api_retries(
            nl_text_for_artifacts,
            synth,
            varprod_rules_linearized=linearize_varprod_rules_excerpt(rules),
            expansion_assessment_digest=expansion_digest,
            interactive_any=interactive_any,
            print_fn=print_fn,
        )
        (work_dir / "critic_report.json").write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        crit_path = work_dir / "critic_result.txt"
        crit_path.write_text(crit_raw, encoding="utf-8")
        summary["critic_result"] = str(crit_path)
        summary["critic_passed"] = critic_report_passed(report)
        print_fn(format_critic_report_terminal(report))

        if critic_report_passed(report):
            break

        if not interactive_any:
            summary["outcome"] = "blocked_critic"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return rules, meta, synth, z3_result, ok, issues, "blocked_critic"

        user_waived = False
        while True:
            if not skip_triage_once or sticky_approved is None:
                cross_approved, cross_ignored = run_critic_finding_triage(
                    report, input_fn=input_fn, print_fn=print_fn
                )
                sticky_approved = set(cross_approved)
                sticky_ignored = set(cross_ignored)
                skip_triage_once = False
            approved = sticky_approved or set()
            ignored = sticky_ignored or set()

            max_findings = critic_semantic_repair_max_findings()
            if max_findings > 0 and len(approved) > max_findings:
                print_fn(
                    f"[policy gate] {len(approved)} findings approved; "
                    f"PIVOT_CRITIC_SEMANTIC_REPAIR_MAX_FINDINGS={max_findings}. "
                    "Use 'retriage' to narrow scope.\n"
                )

            print_fn(format_critic_triage_summary(approved, ignored))
            print_fn(
                format_routing_summary(
                    approved_ids=approved,
                    report=report,
                    with_cross_repair=with_cross_repair,
                )
            )

            _print_semantic_drift_gate(
                print_fn=print_fn,
                short=short_gate,
                compile_attempt_cap=compile_attempt_cap,
                has_triage=True,
            )
            ans = input_fn("> ").strip()
            if ans.lower() == "retriage":
                sticky_approved = None
                sticky_ignored = None
                continue

            if ans == PROCEED_INCOMPLETE_TOKEN:
                summary["critic_passed"] = False
                summary["user_consented_critic_drift"] = True
                h = critic_handoff_dict(
                    report,
                    source_note="user chose PROCEED_INCOMPLETE after DRIFT",
                )
                handoff_path = work_dir / "critic_drift_handoff.json"
                handoff_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                summary["critic_drift_handoff"] = str(handoff_path.resolve())
                user_waived = True
                break

            if ans == REPAIR_CRITIC_DRIFT_TOKEN:
                session_limit = critic_repair_max_rounds()
                if session_limit > 0 and repair_sessions_used >= session_limit:
                    print_fn(
                        f"[policy gate] Max semantic repair sessions ({session_limit}); "
                        f"type {PROCEED_INCOMPLETE_TOKEN!r} or press Enter to abort.\n"
                    )
                    continue
                if no_llm:
                    print_fn("[policy gate] --no-llm set; cannot run repairer.\n")
                    continue
                if not approved:
                    print_fn(
                        "[policy gate] No findings approved for repair; "
                        "re-run triage or type 'retriage'.\n"
                    )
                    continue

                defer, defer_msg = should_defer_semantic_repair(
                    approved_ids=approved,
                    report=report,
                    with_cross_repair=with_cross_repair,
                )
                if defer:
                    print_fn(f"[policy gate] {defer_msg}")
                    continue

                repair_sessions_used += 1
                handoff_path = _handoff_for_semantic_repair(
                    report,
                    approved=approved,
                    ignored=ignored,
                    work_dir=work_dir,
                    source_note="Repairer_Piv semantic from approved critic findings",
                )
                summary["critic_drift_handoff"] = str(handoff_path.resolve())
                summary["critic_repair_approved_count"] = len(
                    json.loads(handoff_path.read_text(encoding="utf-8")).get("findings") or []
                )
                h = json.loads(handoff_path.read_text(encoding="utf-8"))

                result = run_semantic_repair_session(
                    work_dir=work_dir,
                    policy_id=policy_id,
                    rules=rules,
                    handoff=h,
                    repair_session=repair_sessions_used,
                    nl_text_for_artifacts=nl_text_for_artifacts,
                    synth=synth,
                    nl_lines_reg=nl_lines_reg,
                    skip_registry=skip_registry,
                    meta_path=meta_path,
                    nl_for_precheck=nl_for_precheck,
                    summary=summary,
                    print_fn=print_fn,
                    proceed_token=PROCEED_INCOMPLETE_TOKEN,
                )

                if result.success:
                    rules = result.rules
                    meta = result.meta
                    synth = result.synth or synth
                    z3_result = result.z3_result or z3_result
                    ok = result.precheck_ok if result.precheck_ok is not None else ok
                    issues = result.precheck_issues or issues
                    short_gate = False
                    sticky_approved = None
                    sticky_ignored = None
                    break

                extra_handoff: dict[str, Any] = {
                    "last_repair_error_stage": result.last_stage,
                    "repair_session_count": repair_sessions_used,
                }
                if result.last_stage in (None, "rules_compile", "rules_merge"):
                    extra_handoff["last_compile_validation_error"] = result.last_error
                if result.last_stage in ("registry_json", "registry_api"):
                    extra_handoff["last_registry_error"] = result.last_error
                if result.stall_detected:
                    extra_handoff["stall_detected"] = True
                    extra_handoff["stall_stage"] = result.last_stage

                write_critic_repair_handoff(
                    work_dir,
                    report,
                    approved=approved,
                    ignored=ignored,
                    source_note="Semantic repair session failed; awaiting REPAIR",
                    **extra_handoff,
                )

                msg_tail = f" Last error: {result.last_error}" if result.last_error else ""
                print_fn(
                    "[policy gate] Semantic repair did not complete successfully "
                    f"in this session; policy artifacts unchanged.{msg_tail}\n"
                )

                session_limit_after = critic_repair_max_rounds()
                if session_limit_after > 0 and repair_sessions_used >= session_limit_after:
                    summary["outcome"] = BLOCKED_SEMANTIC_REPAIR_COMPILE
                    summary["message"] = (
                        "semantic repair: exhausted repair sessions without a successful rules patch"
                        + msg_tail
                    )
                    summary["critic_passed"] = False
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return rules, meta, synth, z3_result, ok, issues, BLOCKED_SEMANTIC_REPAIR_COMPILE

                short_gate = True
                skip_triage_once = True
                continue

            summary["outcome"] = "blocked_critic"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return rules, meta, synth, z3_result, ok, issues, "blocked_critic"

        if user_waived:
            break

    return rules, meta, synth, z3_result, ok, issues, None


__all__ = [
    "BLOCKED_SEMANTIC_REPAIR_COMPILE",
    "critic_api_auto_retries_max",
    "run_pivot_critic_with_api_retries",
    "run_semantic_critic_interactive_loop",
]
