"""Shared interactive semantic critic loop (NL vs synthetic) used after model updates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.backtranslate import meta_scheme_to_markdown
from pivot_pipeline.critic_agent import (
    critic_handoff_dict,
    critic_report_passed,
    format_critic_report_terminal,
    run_pivot_critic_parsed,
)
from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, REPAIR_CRITIC_DRIFT_TOKEN
from pivot_pipeline.post_model_workflow import critic_repair_compile_attempts_max, critic_repair_max_rounds
from pivot_pipeline.precheck import run_precheck
from pivot_pipeline.registry_pass import registry_pass_from_nl_and_rules
from pivot_pipeline.repairer_piv_agent import append_repairer_trace, run_repairer_piv_semantic
from pivot_pipeline.varprod_trigger_validate import linearize_varprod_rules_excerpt
from pivot_pipeline.z3_compile import run_z3_check

BLOCKED_SEMANTIC_REPAIR_COMPILE = "blocked_semantic_repair_compile"


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

    Returns
    -------
    rules, meta, synth, z3_result, precheck_ok, precheck_issues, early_outcome

    ``early_outcome`` is ``None`` when the loop ends normally (pass or waived).
    Otherwise ``"blocked_critic"``, ``blocked_semantic_repair_compile``, etc. —
    caller should persist run_summary and return.
    """
    repair_sessions_used = 0
    compile_attempt_cap = critic_repair_compile_attempts_max()
    session_limit = critic_repair_max_rounds()

    while True:
        crit_raw, report = run_pivot_critic_parsed(
            nl_text_for_artifacts,
            synth,
            varprod_rules_linearized=linearize_varprod_rules_excerpt(rules),
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
            print_fn(
                "\n[policy gate] Critic reported DRIFT.\n"
                f"  Type {REPAIR_CRITIC_DRIFT_TOKEN!r} to run Repairer_Piv (semantic) from this report, then re-check.\n"
                f"  Type {PROCEED_INCOMPLETE_TOKEN!r} to continue anyway (writes critic_drift_handoff.json for later repair).\n"
                "  Press Enter to abort.\n"
            )
            ans = input_fn("> ").strip()
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
                if repair_sessions_used >= session_limit:
                    print_fn(
                        f"[policy gate] Max semantic repair sessions ({session_limit}); "
                        f"type {PROCEED_INCOMPLETE_TOKEN!r} or press Enter to abort.\n"
                    )
                    continue
                if no_llm:
                    print_fn("[policy gate] --no-llm set; cannot run repairer.\n")
                    continue

                repair_sessions_used += 1
                h = critic_handoff_dict(report, source_note="Repairer_Piv semantic from critic DRIFT")
                last_error: BaseException | None = None
                repaired = False
                compile_feedback: str | None = None

                for compile_attempt in range(compile_attempt_cap):
                    if compile_attempt > 0:
                        print_fn(
                            f"[policy gate] Retrying semantic repair (compile attempt "
                            f"{compile_attempt + 1}/{compile_attempt_cap})...\n"
                        )
                    try:
                        out, json_parse_retry_used = run_repairer_piv_semantic(
                            policy_id=policy_id,
                            rules=rules,
                            handoff=h,
                            effective_nl_excerpt=nl_text_for_artifacts,
                            synthetic_excerpt=synth,
                            compile_validation_error=compile_feedback,
                        )
                    except Exception as re:
                        print_fn(f"[policy gate] Repairer failed: {re}\n")
                        last_error = re
                        break

                    append_repairer_trace(
                        work_dir,
                        {
                            "repair_session": repair_sessions_used,
                            "compile_attempt": compile_attempt + 1,
                            "compile_attempt_cap": compile_attempt_cap,
                            "round": repair_sessions_used,
                            "change_summary": [c.model_dump() for c in out.change_summary],
                            "json_parse_retry_used": json_parse_retry_used,
                        },
                        kind="semantic",
                    )
                    new_rules = out.rules
                    if not skip_registry:
                        try:
                            _, new_rules = registry_pass_from_nl_and_rules(nl_lines_reg, new_rules)
                        except Exception as re:
                            print_fn(
                                f"[policy gate] Registry after repair failed (attempt "
                                f"{compile_attempt + 1}/{compile_attempt_cap}): {re}\n"
                            )
                            last_error = re
                            compile_feedback = str(re)
                            continue
                    try:
                        meta = load_rules_and_compile(policy_id, new_rules)
                    except Exception as ce:
                        print_fn(
                            f"[policy gate] Repaired rules did not compile (attempt "
                            f"{compile_attempt + 1}/{compile_attempt_cap}): {ce}\n"
                        )
                        last_error = ce
                        compile_feedback = str(ce)
                        continue

                    print_fn(
                        f"[policy gate] Repaired rules compiled (attempt "
                        f"{compile_attempt + 1}/{compile_attempt_cap}); updating artifacts.\n"
                    )
                    rules = new_rules
                    extracted_path = work_dir / "rules_extracted.json"
                    extracted_path.write_text(
                        json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    summary["rules_extracted"] = str(extracted_path.resolve())
                    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
                    summary["meta_scheme"] = str(meta_path.resolve())
                    z3_result = run_z3_check(meta)
                    summary["z3"] = z3_result
                    (work_dir / "z3_result.json").write_text(
                        json.dumps(z3_result, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    synth = meta_scheme_to_markdown(meta)
                    (work_dir / "synthetic_en.md").write_text(synth, encoding="utf-8")
                    ok, issues = run_precheck(nl_path=nl_for_precheck, meta=meta)
                    summary["precheck_ok"] = ok
                    summary["precheck_issues"] = issues
                    (work_dir / "precheck.json").write_text(
                        json.dumps({"ok": ok, "issues": issues}, indent=2) + "\n",
                        encoding="utf-8",
                    )
                    (work_dir / "rules_after_semantic_repair.json").write_text(
                        json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    repaired = True
                    break

                if repaired:
                    break

                msg_tail = f" Last error: {last_error}" if last_error is not None else ""
                print_fn(
                    "[policy gate] Semantic repair did not yield compiling rules after "
                    f"{compile_attempt_cap} attempt(s) in this session; policy artifacts unchanged.{msg_tail}\n"
                )
                if repair_sessions_used >= session_limit:
                    summary["outcome"] = BLOCKED_SEMANTIC_REPAIR_COMPILE
                    summary["message"] = (
                        "semantic repair: exhausted repair sessions without a compiling rules patch"
                        + msg_tail
                    )
                    summary["critic_passed"] = False
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return rules, meta, synth, z3_result, ok, issues, BLOCKED_SEMANTIC_REPAIR_COMPILE
                continue

            summary["outcome"] = "blocked_critic"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return rules, meta, synth, z3_result, ok, issues, "blocked_critic"

        if user_waived:
            break
        # Otherwise: inner loop exited after a successful compile (repaired); re-run critic.

    return rules, meta, synth, z3_result, ok, issues, None


__all__ = ["BLOCKED_SEMANTIC_REPAIR_COMPILE", "run_semantic_critic_interactive_loop"]
