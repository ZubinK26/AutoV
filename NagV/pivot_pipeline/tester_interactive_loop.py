"""Interactive Pivot Tester loop with per-finding triage and Test-Repairer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.exceptions import PivotPipelineUserAbort
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.assessment_linearize import build_and_write_assessment_artifacts
from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.post_model_workflow import (
    TesterReport,
    format_tester_report_terminal,
    run_pivot_tester_with_repairs,
)
from pivot_pipeline.repair_apply import apply_repaired_rules_and_refresh
from pivot_pipeline.rules_document import envelope_from_summary_or_body
from pivot_pipeline.tester_repair_resume import (
    TesterRepairResumeError,
    load_last_test_repair_compile_error,
    triage_sets_from_handoff,
    validate_tester_repair_resume,
)
from pivot_pipeline.test_repair_registry import (
    is_repairer_api_error,
    run_test_repair_registry,
    test_repair_count_api_as_attempt,
    test_repair_registry_attempts_max,
)
from pivot_pipeline.tester_repairer_agent import (
    MergeRepairerOutputError,
    append_test_repairer_trace,
    precompile_repaired_rules,
    run_test_repairer,
    test_repair_compile_attempts_max,
    test_repair_max_rounds,
    tester_repair_handoff_dict,
)

BLOCKED_TEST_REPAIR_COMPILE = "blocked_test_repair_compile"
REPAIR_TOKEN = REPAIR_CRITIC_DRIFT_TOKEN


def tester_report_passed(report: TesterReport) -> bool:
    return report.verdict == "ok"


def run_finding_triage(
    report: TesterReport,
    *,
    input_fn: Callable[[str], str],
    print_fn: Callable[..., None],
) -> tuple[set[str], set[str]]:
    """Per-finding approve (a) / ignore (i); q quits triage early."""
    approved: set[str] = set()
    ignored: set[str] = set()
    findings = sorted(report.findings, key=lambda f: f.id)
    total = len(findings)
    if total == 0:
        return approved, ignored

    print_fn("\n=== Tester finding triage ===\n")
    for idx, f in enumerate(findings, start=1):
        print_fn(
            f"Finding {idx} of {total}: [{f.id}] {f.severity} / {f.category}\n"
            f"  NL: {f.nl_pointer or '(none)'}\n"
            f"  Formal: {f.formal_pointer or '(none)'}\n"
            f"  {f.explanation}\n"
        )
        while True:
            ans = input_fn("  a = approve for repair   i = ignore   q = quit triage: ").strip().lower()
            if ans == "a":
                approved.add(f.id)
                break
            if ans == "i":
                ignored.add(f.id)
                break
            if ans == "q":
                print_fn("")
                return approved, ignored
            print_fn("  Invalid choice; use a, i, or q.\n")

    print_fn("")
    return approved, ignored


def _format_triage_summary(
    report: TesterReport,
    approved: set[str],
    ignored: set[str],
) -> str:
    pending = [f.id for f in report.findings if f.id not in approved and f.id not in ignored]
    lines = ["Triage summary:"]
    lines.append(f"  Approved for repair: {', '.join(sorted(approved)) or '(none)'}")
    lines.append(f"  Ignored: {', '.join(sorted(ignored)) or '(none)'}")
    if pending:
        lines.append(f"  Pending (not sent to repair): {', '.join(pending)}")
    return "\n".join(lines) + "\n"


def _write_tester_repair_handoff(
    work_dir: Path,
    report: TesterReport,
    *,
    approved: set[str],
    ignored: set[str],
    source_note: str,
    last_compile_validation_error: str | None = None,
    last_repair_error_stage: str | None = None,
    last_registry_error: str | None = None,
    repair_session_count: int | None = None,
) -> Path:
    handoff_path = work_dir / "tester_repair_handoff.json"
    tester_path = work_dir / "tester_report.json"
    h = tester_repair_handoff_dict(
        report,
        approved_ids=sorted(approved),
        ignored_ids=sorted(ignored),
        full_report_path=tester_path,
        source_note=source_note,
        last_compile_validation_error=last_compile_validation_error,
        last_repair_error_stage=last_repair_error_stage,
        last_registry_error=last_registry_error,
        repair_session_count=repair_session_count,
    )
    handoff_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return handoff_path


def _print_policy_gate(
    *,
    print_fn: Callable[..., None],
    n_total: int,
    n_approved: int,
    short: bool,
    compile_attempt_cap: int,
    resume_from_handoff: bool = False,
) -> None:
    if resume_from_handoff:
        print_fn(
            f"[policy gate] Resuming Test-Repairer from saved handoff "
            f"({n_approved} approved finding(s); no Pivot Tester LLM).\n"
            f"  Type {REPAIR_TOKEN!r} to run Test-Repairer (up to {compile_attempt_cap} compile tries per REPAIR), "
            f"{PROCEED_INCOMPLETE_TOKEN!r} to waive, or Enter to abort.\n"
            f"  Type 'retriage' to re-run finding triage (a/i).\n"
        )
    elif short:
        print_fn(
            f"[policy gate] Compile budget exhausted ({compile_attempt_cap} attempts in last REPAIR); "
            "policy artifacts unchanged.\n"
            f"  Same approved findings still active ({n_approved} of {n_total}). "
            f"No new Pivot Tester call until repair succeeds.\n"
            f"  Type {REPAIR_TOKEN!r} to run Test-Repairer again, {PROCEED_INCOMPLETE_TOKEN!r} to waive, "
            "or Enter to abort.\n"
            f"  Type 'retriage' to re-run finding triage (a/i).\n"
        )
    else:
        print_fn(
            f"[policy gate] Tester reported issues ({n_total} total; {n_approved} approved for repair).\n"
            f"  Type {REPAIR_TOKEN!r} to run Test-Repairer on approved findings only, then re-run Tester.\n"
            f"  Type {PROCEED_INCOMPLETE_TOKEN!r} to continue without repair "
            f"(writes tester_repair_handoff.json with approvals/ignores for audit).\n"
            "  Press Enter to abort.\n"
        )


def run_tester_interactive_loop(
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
    with_test_repair: bool,
    fail_on_tester_findings: bool,
    resume_tester_repair: bool = False,
    retriage_tester: bool = False,
    print_fn: Callable[..., None],
    input_fn: Callable[[str], str],
    summary: dict[str, Any],
    synth: str,
    meta: Any,
    z3_result: dict[str, Any],
    ok: bool,
    issues: list[Any],
    linearized: str | None,
    refresh_varprod_trigger_check: Callable[[], bool],
) -> tuple[
    list[dict[str, Any]],
    Any,
    str,
    dict[str, Any],
    bool,
    list[Any],
    str | None,
    str | None,
]:
    """
    Run tester; optionally triage findings and Test-Repairer until ok, waive, or abort.

    Returns ``(rules, meta, synth, z3_result, precheck_ok, precheck_issues, linearized, early_outcome)``.
    """
    session_limit = test_repair_max_rounds() if with_test_repair else 0
    compile_attempt_cap = test_repair_compile_attempts_max()
    repair_sessions_used = 0
    summary["tester_repair_rounds"] = 0
    skip_triage_once = False
    sticky_approved: set[str] | None = None
    sticky_ignored: set[str] | None = None

    if linearized is None:
        linearized = build_and_write_assessment_artifacts(
            work_dir=work_dir, rules=rules, summary=summary
        )

    tester_rep: TesterReport | None = None
    if resume_tester_repair:
        try:
            tester_rep, handoff = validate_tester_repair_resume(work_dir)
        except TesterRepairResumeError as e:
            summary["outcome"] = BLOCKED_TEST_REPAIR_COMPILE
            summary["message"] = str(e)
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return rules, meta, synth, z3_result, ok, issues, linearized, BLOCKED_TEST_REPAIR_COMPILE
        sticky_approved, sticky_ignored = triage_sets_from_handoff(handoff)
        skip_triage_once = not retriage_tester
        resume_gate = not retriage_tester
        summary["tester_resume_repair"] = True
        summary["tester_verdict"] = tester_rep.verdict
        summary["tester_report"] = str((work_dir / "tester_report.json").resolve())
        print_fn(
            "\n[pivot pipeline] --resume-tester-repair: skipping Pivot Tester LLM; "
            f"using saved report and {len(sticky_approved)} approved finding(s).\n"
        )
        print_fn(format_tester_report_terminal(tester_rep))
        if not interactive_any:
            summary["tester_passed"] = False
            summary["outcome"] = "blocked_tester"
            summary["message"] = "resume-tester-repair requires --interactive-tester or --interactive-policy"
            return rules, meta, synth, z3_result, ok, issues, linearized, "blocked_tester"

    while True:
        if tester_rep is None:
            _raw_t, tester_rep, json_repair_attempts = run_pivot_tester_with_repairs(
                processed_nl=nl_text_for_artifacts,
                linearized_model=linearized or "",
                work_dir=work_dir,
            )
            summary["tester_json_repair_attempts"] = json_repair_attempts
            tester_path = work_dir / "tester_report.json"
            tester_path.write_text(tester_rep.model_dump_json(indent=2) + "\n", encoding="utf-8")
            (work_dir / "tester_result.txt").write_text(_raw_t, encoding="utf-8")
            summary["tester_verdict"] = tester_rep.verdict
            summary["tester_compared_against"] = tester_rep.compared_against
            summary["tester_report"] = str(tester_path.resolve())
            print_fn(format_tester_report_terminal(tester_rep))

            if tester_report_passed(tester_rep):
                summary["tester_passed"] = True
                return rules, meta, synth, z3_result, ok, issues, linearized, None

            if not interactive_any:
                summary["tester_passed"] = False
                if fail_on_tester_findings:
                    summary["outcome"] = "blocked_tester"
                    summary["message"] = "Tester reported issues (--fail-on-tester-findings)"
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return rules, meta, synth, z3_result, ok, issues, linearized, "blocked_tester"
                return rules, meta, synth, z3_result, ok, issues, linearized, None

        assert tester_rep is not None
        user_waived = False
        short_gate = False
        resume_gate = False
        while True:
            if skip_triage_once and sticky_approved is not None:
                approved = set(sticky_approved)
                ignored = set(sticky_ignored or ())
                skip_triage_once = False
                short_gate = not resume_gate
                print_fn(_format_triage_summary(tester_rep, approved, ignored))
            else:
                short_gate = False
                approved, ignored = run_finding_triage(
                    tester_rep,
                    input_fn=input_fn,
                    print_fn=print_fn,
                )
                print_fn(_format_triage_summary(tester_rep, approved, ignored))
                sticky_approved = set(approved)
                sticky_ignored = set(ignored)

            n_total = len(tester_rep.findings)
            n_approved = len(approved)
            _print_policy_gate(
                print_fn=print_fn,
                n_total=n_total,
                n_approved=n_approved,
                short=short_gate,
                compile_attempt_cap=compile_attempt_cap,
                resume_from_handoff=resume_gate,
            )
            if resume_gate:
                resume_gate = False
            ans = input_fn("[policy gate] Tester issues — REPAIR / PROCEED_INCOMPLETE / Enter abort: ").strip()
            ans_norm = ans.strip().upper()

            if not ans:
                raise PivotPipelineUserAbort("Tester gate: empty input (abort)")

            if ans.lower() == "retriage":
                skip_triage_once = False
                sticky_approved = None
                continue

            if ans_norm == PROCEED_INCOMPLETE_TOKEN:
                handoff_path = _write_tester_repair_handoff(
                    work_dir,
                    tester_rep,
                    approved=approved,
                    ignored=ignored,
                    source_note="user chose PROCEED_INCOMPLETE after tester issues",
                    repair_session_count=repair_sessions_used,
                )
                summary["tester_repair_handoff"] = str(handoff_path.resolve())
                summary["user_consented_tester_issues"] = True
                summary["tester_passed"] = True
                user_waived = True
                break

            if ans_norm == REPAIR_TOKEN:
                if not with_test_repair:
                    print_fn(
                        "[policy gate] --with-test-repair not set; cannot run Test-Repairer.\n"
                    )
                    continue
                if n_approved == 0:
                    print_fn(
                        "[policy gate] No findings approved for repair; approve at least one (a) or "
                        f"type {PROCEED_INCOMPLETE_TOKEN!r}.\n"
                    )
                    continue
                if repair_sessions_used >= session_limit:
                    print_fn(
                        f"[policy gate] Max Test-Repairer rounds ({session_limit}); "
                        f"type {PROCEED_INCOMPLETE_TOKEN!r} or press Enter to abort.\n"
                    )
                    summary["outcome"] = BLOCKED_TEST_REPAIR_COMPILE
                    summary["message"] = (
                        f"test repair: exhausted {session_limit} REPAIR session(s) without compiling patch"
                    )
                    summary["tester_passed"] = False
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return (
                        rules,
                        meta,
                        synth,
                        z3_result,
                        ok,
                        issues,
                        linearized,
                        BLOCKED_TEST_REPAIR_COMPILE,
                    )
                if no_llm:
                    print_fn("[policy gate] --no-llm set; cannot run Test-Repairer.\n")
                    continue

                repair_sessions_used += 1
                summary["tester_repair_rounds"] = repair_sessions_used
                use_saved_error = short_gate or resume_tester_repair
                if resume_tester_repair:
                    resume_tester_repair = False
                initial_feedback = (
                    load_last_test_repair_compile_error(work_dir) if use_saved_error else None
                )
                handoff_path = _write_tester_repair_handoff(
                    work_dir,
                    tester_rep,
                    approved=approved,
                    ignored=ignored,
                    source_note="Test-Repairer from approved tester findings",
                    last_compile_validation_error=initial_feedback,
                    repair_session_count=repair_sessions_used,
                )
                summary["tester_repair_handoff"] = str(handoff_path.resolve())
                h = json.loads(handoff_path.read_text(encoding="utf-8"))

                last_error: BaseException | None = None
                repaired = False
                compile_feedback: str | None = initial_feedback
                merge_feedback: str | None = None
                last_stage: str | None = None
                last_registry_error: str | None = None
                registry_cap = test_repair_registry_attempts_max()
                count_api = test_repair_count_api_as_attempt()
                compile_attempt = 0
                api_retries_no_burn = 0

                while compile_attempt < compile_attempt_cap:
                    if compile_attempt > 0:
                        print_fn(
                            f"[policy gate] Retrying Test-Repairer (compile attempt "
                            f"{compile_attempt + 1}/{compile_attempt_cap})...\n"
                        )
                    try:
                        out, json_parse_retry_used = run_test_repairer(
                            policy_id=policy_id,
                            rules=rules,
                            handoff=h,
                            processed_nl_excerpt=nl_text_for_artifacts,
                            linearized_excerpt=linearized or "",
                            compile_validation_error=compile_feedback,
                            merge_validation_error=merge_feedback,
                        )
                    except MergeRepairerOutputError as me:
                        print_fn(
                            f"[policy gate] Test-Repairer returned incomplete rules "
                            f"(attempt {compile_attempt + 1}/{compile_attempt_cap}): {me}\n"
                        )
                        last_error = me
                        last_stage = "rules_merge"
                        merge_feedback = str(me)
                        compile_feedback = None
                        append_test_repairer_trace(
                            work_dir,
                            {
                                "repair_session": repair_sessions_used,
                                "compile_attempt": compile_attempt + 1,
                                "error_stage": "rules_merge",
                                "error": str(me),
                                "approved_finding_ids": sorted(approved),
                            },
                        )
                        compile_attempt += 1
                        continue
                    except Exception as re:
                        stage = "repairer_api" if is_repairer_api_error(re) else "repairer_json"
                        print_fn(f"[policy gate] Test-Repairer failed ({stage}): {re}\n")
                        last_error = re
                        last_stage = stage
                        append_test_repairer_trace(
                            work_dir,
                            {
                                "repair_session": repair_sessions_used,
                                "compile_attempt": compile_attempt + 1,
                                "error_stage": stage,
                                "error": str(re),
                                "approved_finding_ids": sorted(approved),
                            },
                        )
                        if stage == "repairer_api" and not count_api:
                            api_retries_no_burn += 1
                            if api_retries_no_burn < 3:
                                continue
                        break

                    append_test_repairer_trace(
                        work_dir,
                        {
                            "repair_session": repair_sessions_used,
                            "compile_attempt": compile_attempt + 1,
                            "compile_attempt_cap": compile_attempt_cap,
                            "round": repair_sessions_used,
                            "change_summary": [c.model_dump() for c in out.change_summary],
                            "json_parse_retry_used": json_parse_retry_used,
                            "approved_finding_ids": sorted(approved),
                        },
                    )
                    merged_rules = out.rules
                    rules_before = rules

                    try:
                        new_rules = precompile_repaired_rules(policy_id, merged_rules)
                    except Exception as ce:
                        print_fn(
                            f"[policy gate] Test-repaired rules did not compile (attempt "
                            f"{compile_attempt + 1}/{compile_attempt_cap}): {ce}\n"
                        )
                        last_error = ce
                        last_stage = "rules_compile"
                        compile_feedback = str(ce)
                        merge_feedback = None
                        append_test_repairer_trace(
                            work_dir,
                            {
                                "repair_session": repair_sessions_used,
                                "compile_attempt": compile_attempt + 1,
                                "error_stage": "rules_compile",
                                "compile_validation_error": str(ce),
                                "approved_finding_ids": sorted(approved),
                            },
                        )
                        compile_attempt += 1
                        continue

                    registry_ok = False
                    if skip_registry:
                        registry_ok = True
                    else:
                        for reg_attempt in range(registry_cap):
                            try:
                                _reg, new_rules, reused = run_test_repair_registry(
                                    work_dir=work_dir,
                                    nl_lines_reg=nl_lines_reg,
                                    rules_before=rules_before,
                                    merged_rules=new_rules,
                                    cli_skip_registry=False,
                                    llm=pivot_llm_complete,
                                )
                                if reused:
                                    print_fn(
                                        "[policy gate] Registry skipped (slug set unchanged); "
                                        "reusing identifier_registry.json.\n"
                                    )
                                registry_ok = True
                                break
                            except Exception as re:
                                reg_stage = (
                                    "registry_api"
                                    if is_repairer_api_error(re)
                                    else "registry_json"
                                )
                                last_registry_error = str(re)
                                last_stage = reg_stage
                                last_error = re
                                print_fn(
                                    f"[policy gate] Registry pass failed ({reg_stage}) "
                                    f"(registry attempt {reg_attempt + 1}/{registry_cap}): {re}\n"
                                )
                                append_test_repairer_trace(
                                    work_dir,
                                    {
                                        "repair_session": repair_sessions_used,
                                        "compile_attempt": compile_attempt + 1,
                                        "registry_attempt": reg_attempt + 1,
                                        "error_stage": reg_stage,
                                        "error": str(re),
                                        "approved_finding_ids": sorted(approved),
                                    },
                                )
                        if not registry_ok:
                            break

                    try:
                        rules, meta, synth, z3_result, ok, issues, linearized = (
                            apply_repaired_rules_and_refresh(
                                work_dir=work_dir,
                                policy_id=policy_id,
                                rules=new_rules,
                                meta_path=meta_path,
                                nl_for_precheck=nl_for_precheck,
                                summary=summary,
                                after_rules_basename="rules_after_test_repair.json",
                                refresh_linearized=True,
                                rules_envelope=envelope_from_summary_or_body(summary),
                            )
                        )
                    except Exception as ce:
                        print_fn(
                            f"[policy gate] Artifact refresh failed after test repair "
                            f"(attempt {compile_attempt + 1}/{compile_attempt_cap}): {ce}\n"
                        )
                        last_error = ce
                        last_stage = "rules_compile"
                        compile_feedback = str(ce)
                        compile_attempt += 1
                        continue

                    refresh_varprod_trigger_check()
                    print_fn(
                        f"[policy gate] Test-repaired rules compiled (attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap}); updating artifacts.\n"
                    )
                    repaired = True
                    break

                if repaired:
                    tester_rep = None
                    sticky_approved = None
                    sticky_ignored = None
                    break

                msg_tail = f" Last error: {last_error}" if last_error is not None else ""
                compile_err = (
                    compile_feedback
                    if last_stage in (None, "rules_compile", "rules_merge")
                    else None
                )
                if last_stage == "rules_compile" and not compile_err and last_error is not None:
                    compile_err = str(last_error)
                _write_tester_repair_handoff(
                    work_dir,
                    tester_rep,
                    approved=approved,
                    ignored=ignored,
                    source_note="Test-Repairer compile budget exhausted; awaiting REPAIR",
                    last_compile_validation_error=compile_err,
                    last_repair_error_stage=last_stage,
                    last_registry_error=last_registry_error,
                    repair_session_count=repair_sessions_used,
                )
                if repair_sessions_used >= session_limit:
                    summary["outcome"] = BLOCKED_TEST_REPAIR_COMPILE
                    summary["message"] = (
                        "test repair: exhausted repair sessions without a compiling rules patch"
                        + msg_tail
                    )
                    summary["tester_passed"] = False
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return (
                        rules,
                        meta,
                        synth,
                        z3_result,
                        ok,
                        issues,
                        linearized,
                        BLOCKED_TEST_REPAIR_COMPILE,
                    )
                skip_triage_once = True
                sticky_approved = set(approved)
                sticky_ignored = set(ignored)
                continue

            print_fn(
                f"[policy gate] Unrecognized input {ans!r}; use {REPAIR_TOKEN!r}, "
                f"{PROCEED_INCOMPLETE_TOKEN!r}, 'retriage', or Enter to abort.\n"
            )
            continue

        if user_waived:
            return rules, meta, synth, z3_result, ok, issues, linearized, None
        if resume_tester_repair and tester_rep is not None:
            resume_tester_repair = False
        # Successful repair or resume path: outer loop re-runs tester (tester_rep cleared).


__all__ = [
    "BLOCKED_TEST_REPAIR_COMPILE",
    "run_finding_triage",
    "run_tester_interactive_loop",
    "tester_report_passed",
]
