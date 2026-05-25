"""Interactive Pivot Tester loop with per-finding triage and Test-Repairer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.exceptions import PivotPipelineUserAbort
from pivot_pipeline.linearize_rules import build_and_write_linearized, linearized_model_artifact_path
from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.post_model_workflow import (
    TesterReport,
    format_tester_report_terminal,
    run_pivot_tester,
)
from pivot_pipeline.registry_pass import registry_pass_from_nl_and_rules
from pivot_pipeline.repair_apply import apply_repaired_rules_and_refresh
from pivot_pipeline.tester_repairer_agent import (
    append_test_repairer_trace,
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
) -> Path:
    handoff_path = work_dir / "tester_repair_handoff.json"
    tester_path = work_dir / "tester_report.json"
    h = tester_repair_handoff_dict(
        report,
        approved_ids=sorted(approved),
        ignored_ids=sorted(ignored),
        full_report_path=tester_path,
        source_note=source_note,
    )
    handoff_path.write_text(json.dumps(h, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return handoff_path


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

    if linearized is None:
        linearized = build_and_write_linearized(work_dir=work_dir, rules=rules)
        summary["linearized_model_for_cross_critic"] = str(
            linearized_model_artifact_path(work_dir).resolve()
        )

    while True:
        _raw_t, tester_rep = run_pivot_tester(
            processed_nl=nl_text_for_artifacts,
            linearized_model=linearized or "",
        )
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

        user_waived = False
        while True:
            approved, ignored = run_finding_triage(
                tester_rep,
                input_fn=input_fn,
                print_fn=print_fn,
            )
            print_fn(_format_triage_summary(tester_rep, approved, ignored))

            n_total = len(tester_rep.findings)
            n_approved = len(approved)
            print_fn(
                f"[policy gate] Tester reported issues ({n_total} total; {n_approved} approved for repair).\n"
                f"  Type {REPAIR_TOKEN!r} to run Test-Repairer on approved findings only, then re-run Tester.\n"
                f"  Type {PROCEED_INCOMPLETE_TOKEN!r} to continue without repair "
                f"(writes tester_repair_handoff.json with approvals/ignores for audit).\n"
                "  Press Enter to abort.\n"
            )
            ans = input_fn("[policy gate] Tester issues — REPAIR / PROCEED_INCOMPLETE / Enter abort: ").strip()

            if not ans:
                raise PivotPipelineUserAbort("Tester gate: empty input (abort)")

            if ans == PROCEED_INCOMPLETE_TOKEN:
                handoff_path = _write_tester_repair_handoff(
                    work_dir,
                    tester_rep,
                    approved=approved,
                    ignored=ignored,
                    source_note="user chose PROCEED_INCOMPLETE after tester issues",
                )
                summary["tester_repair_handoff"] = str(handoff_path.resolve())
                summary["user_consented_tester_issues"] = True
                summary["tester_passed"] = True
                user_waived = True
                break

            if ans == REPAIR_TOKEN:
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
                    continue
                if no_llm:
                    print_fn("[policy gate] --no-llm set; cannot run Test-Repairer.\n")
                    continue

                repair_sessions_used += 1
                summary["tester_repair_rounds"] = repair_sessions_used
                handoff_path = _write_tester_repair_handoff(
                    work_dir,
                    tester_rep,
                    approved=approved,
                    ignored=ignored,
                    source_note="Test-Repairer from approved tester findings",
                )
                summary["tester_repair_handoff"] = str(handoff_path.resolve())
                h = json.loads(handoff_path.read_text(encoding="utf-8"))

                last_error: BaseException | None = None
                repaired = False
                compile_feedback: str | None = None

                for compile_attempt in range(compile_attempt_cap):
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
                        )
                    except Exception as re:
                        print_fn(f"[policy gate] Test-Repairer failed: {re}\n")
                        last_error = re
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
                    new_rules = out.rules
                    if not skip_registry:
                        try:
                            _, new_rules = registry_pass_from_nl_and_rules(nl_lines_reg, new_rules)
                        except Exception as re:
                            print_fn(
                                f"[policy gate] Registry after test repair failed (attempt "
                                f"{compile_attempt + 1}/{compile_attempt_cap}): {re}\n"
                            )
                            last_error = re
                            compile_feedback = str(re)
                            continue
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
                            )
                        )
                    except Exception as ce:
                        print_fn(
                            f"[policy gate] Test-repaired rules did not compile (attempt "
                            f"{compile_attempt + 1}/{compile_attempt_cap}): {ce}\n"
                        )
                        last_error = ce
                        compile_feedback = str(ce)
                        continue

                    refresh_varprod_trigger_check()
                    print_fn(
                        f"[policy gate] Test-repaired rules compiled (attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap}); updating artifacts.\n"
                    )
                    repaired = True
                    break

                if repaired:
                    break

                msg_tail = f" Last error: {last_error}" if last_error is not None else ""
                print_fn(
                    "[policy gate] Test repair did not yield compiling rules after "
                    f"{compile_attempt_cap} attempt(s) in this session; policy artifacts unchanged.{msg_tail}\n"
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
                continue

            summary["outcome"] = "blocked_tester"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return rules, meta, synth, z3_result, ok, issues, linearized, "blocked_tester"

        if user_waived:
            return rules, meta, synth, z3_result, ok, issues, linearized, None
        # Successful repair: outer loop re-runs tester.


__all__ = [
    "BLOCKED_TEST_REPAIR_COMPILE",
    "run_finding_triage",
    "run_tester_interactive_loop",
    "tester_report_passed",
]
