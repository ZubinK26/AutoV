"""Orchestrate pivot phases (see ``NagV/Extract-Pivot.md``)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_NAGV_ROOT = Path(__file__).resolve().parents[1]
if str(_NAGV_ROOT) not in sys.path:
    sys.path.insert(0, str(_NAGV_ROOT))


def run_pivot_pipeline(
    *,
    repo_root: Path,
    work_dir: Path,
    nl_source: Path,
    rules_json: Path | None,
    skip_phase0: bool,
    reset_progress: bool,
    rules_per_chunk: int,
    skip_critic: bool = True,
    no_llm: bool = False,
    skip_registry: bool = False,
    extract_only: bool = False,
    interactive_policy: bool = False,
    interactive_extract_abort: bool = False,
    interactive_cross_coherence: bool = False,
    with_tester: bool = False,
    fail_on_tester_findings: bool = False,
    repairer_max_rounds: int = 2,
    with_cross_critic: bool = False,
    with_cross_repair: bool = False,
    cross_coherence_skip_critic_gate: bool = False,
    fail_on_precheck_warnings: bool = False,
    fail_on_varprod_trigger: bool = False,
    with_template_generator: bool = False,
    template_suite_path: Path | None = None,
    input_fn: Callable[[str], str] | None = None,
    print_fn: Callable[..., None] = print,
) -> dict[str, Any]:
    from pivot_pipeline.backtranslate import meta_scheme_to_markdown
    from pivot_pipeline.exceptions import PivotPipelineUserAbort
    from pivot_pipeline.extract import ExtractAbort, ExtractValidationError, extract_rules_from_lines
    from pivot_pipeline.ir import load_rules_and_compile
    from pivot_pipeline.cross_critic_agent import (
        cross_critic_handoff_dict,
        cross_critic_report_ok,
        format_cross_critic_report_terminal,
        run_cross_critic_parsed,
    )
    from pivot_pipeline.cross_repairer_agent import (
        append_cross_repairer_trace,
        cross_repair_max_rounds,
        run_cross_repairer,
    )
    from pivot_pipeline.linearize_rules import linearize_rules_for_cross_critic
    from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN, enforce_wfm_rule_coverage
    from pivot_pipeline.post_model_workflow import format_tester_report_terminal, run_pivot_tester
    from pivot_pipeline.precheck import run_precheck
    from pivot_pipeline.registry_pass import registry_pass_from_nl_and_rules
    from pivot_pipeline.repairer_piv_agent import append_repairer_trace, run_repairer_piv_structural
    from pivot_pipeline.semantic_critic_loop import run_semantic_critic_interactive_loop
    from pivot_pipeline.varprod_trigger_validate import (
        validate_varprod_triggers,
        varprod_skip_rule_ids_from_env,
        write_ir_structure_check,
    )
    from pivot_pipeline.z3_compile import run_z3_check
    from pivot_wfm.aggregate import aggregate_pivot_wfm_nl
    from pivot_wfm.run_wfm_phase import run_pivot_wfm_until_complete
    from wfm_orchestration.nl_chunk_policy_pipeline import parse_nl_rules

    try:
        from nagv.agent_trace import configure_agent_trace
    except ImportError:
        configure_agent_trace = lambda _p: None  # type: ignore[assignment]

    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    configure_agent_trace(work_dir)

    if input_fn is None:
        input_fn = input

    summary: dict[str, Any] = {"nl_source": str(nl_source.resolve()), "work_dir": str(work_dir)}

    interactive_any = interactive_policy or interactive_extract_abort
    interactive_cross_any = interactive_policy or interactive_cross_coherence
    if interactive_any:
        summary["interactive_policy"] = True
    if interactive_cross_coherence:
        summary["interactive_cross_coherence"] = True

    if not skip_phase0:
        try:
            rc = run_pivot_wfm_until_complete(
                repo_root=repo_root,
                nl_file=nl_source,
                work_dir=work_dir,
                rules_per_chunk=rules_per_chunk,
                reset_progress=reset_progress,
                print_fn=print_fn,
                interactive_policy=interactive_any,
                input_fn=input_fn,
            )
        except PivotPipelineUserAbort as e:
            summary["outcome"] = "blocked_user_abort"
            summary["message"] = str(e)
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        summary["phase0_exit_code"] = rc
        if rc != 0:
            summary["outcome"] = "blocked_wfm_chunk_coverage" if rc == 3 else "blocked_phase0"
            if rc == 3:
                summary["message"] = (
                    "Pivot WFM failed per-chunk line coverage (non-interactive repair, or fix prompts / NL). "
                    "Re-run with --interactive-policy for scope-rewrite + retry, or set "
                    "PIVOT_WFM_COVERAGE_MAX_WFM_ATTEMPTS."
                )
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        agg = aggregate_pivot_wfm_nl(repo_root=repo_root, work_dir=work_dir, print_fn=print_fn)
        summary["wfm_forward_lines"] = agg.forward_line_count
        if not agg.ok:
            summary["outcome"] = "blocked_wfm_aggregate"
            summary["blocking_lines"] = [b.get("line_index") for b in agg.blocking_lines]
            summary["message"] = agg.message
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

        nl_for_count_gate = nl_source.resolve()
        eff_nl = work_dir / "pivot_wfm_effective_source.nl"
        if eff_nl.is_file():
            nl_for_count_gate = eff_nl.resolve()
            summary["wfm_coverage_source"] = str(nl_for_count_gate)

        meta_path = work_dir / "pivot_wfm_phase0_meta.json"
        if meta_path.is_file():
            try:
                phase0_meta = json.loads(meta_path.read_text(encoding="utf-8"))
                summary["phase0_chunks_this_invocation"] = phase0_meta.get("chunks_this_invocation")
                if phase0_meta.get("chunks_this_invocation") == 0:
                    print_fn(
                        "[pivot pipeline] Phase 0 ran **0 WFM chunks** this invocation (progress already complete); "
                        "handoffs were not refreshed. If the rule-count gate fails, re-run with **--reset-progress**.\n"
                    )
            except (json.JSONDecodeError, OSError):
                pass

        try:
            ok_cov, consent_inc = enforce_wfm_rule_coverage(
                nl_source=nl_for_count_gate,
                wfm_nl_text=agg.nl,
                interactive_policy=interactive_any,
                print_fn=print_fn,
                input_fn=input_fn,
            )
        except PivotPipelineUserAbort as e:
            summary["outcome"] = "blocked_user_abort"
            summary["message"] = str(e)
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

        if not ok_cov:
            n_in = len(parse_nl_rules(nl_for_count_gate.read_text(encoding="utf-8")))
            n_out = len(parse_nl_rules(agg.nl))
            summary["outcome"] = "blocked_wfm_coverage"
            summary["source_rule_count"] = n_in
            summary["wfm_rule_count"] = n_out
            tip = ""
            if summary.get("phase0_chunks_this_invocation") == 0:
                tip = " Phase 0 did not re-run WFM; add --reset-progress with the same --work-dir to rebuild handoffs."
            summary["message"] = (
                "WFM normalized NL rule count does not match the coverage source NL "
                "(see source_rule_count vs wfm_rule_count). "
                "Pass --interactive-policy and type PROCEED_INCOMPLETE at the prompt to continue anyway, "
                "or fix pivot WFM so every source rule line is preserved."
                + tip
            )
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        if consent_inc:
            summary["user_consented_wfm_incomplete_coverage"] = True

        normalized_nl_path = work_dir / "phase0_normalized_nl.txt"
        normalized_nl_path.write_text(agg.nl + "\n", encoding="utf-8")
        summary["phase0_normalized_nl"] = str(normalized_nl_path)
        nl_for_precheck = normalized_nl_path
    else:
        norm_path = work_dir / "phase0_normalized_nl.txt"
        if norm_path.is_file() and norm_path.stat().st_size > 0:
            nl_for_precheck = norm_path.resolve()
            summary["phase0_normalized_nl"] = str(nl_for_precheck)
            print_fn(
                "[pivot pipeline] --skip-phase0: using existing phase0_normalized_nl.txt in work_dir for extract "
                f"({nl_for_precheck}). policy_id still from --input ({nl_source.name}).\n"
            )
        else:
            nl_for_precheck = nl_source.resolve()
            print_fn(
                "[pivot pipeline] --skip-phase0: no non-empty phase0_normalized_nl.txt in work_dir — "
                f"using raw --input for extract ({nl_source}).\n"
            )

    nl_text_for_artifacts = nl_for_precheck.read_text(encoding="utf-8")
    (work_dir / "rules_source.txt").write_text(nl_text_for_artifacts, encoding="utf-8")

    policy_id = nl_source.stem
    rules: list[dict[str, Any]]

    use_file = rules_json is not None and rules_json.is_file()
    if use_file:
        rules_body = json.loads(rules_json.read_text(encoding="utf-8"))
        policy_id = str(rules_body.get("policy_id") or policy_id)
        raw_rules = rules_body.get("rules")
        if not isinstance(raw_rules, list):
            raise ValueError("--rules-json must contain { policy_id?, rules: [...] }")
        rules = raw_rules
        summary["rules_json"] = str(rules_json.resolve())
    elif no_llm:
        summary["outcome"] = "blocked_no_rules_json"
        summary["message"] = (
            "No --rules-json and --no-llm set — provide a rules JSON file or enable LLM extraction "
            "(omit --no-llm)."
        )
        (work_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return summary
    else:
        nl_lines = parse_nl_rules(nl_text_for_artifacts)
        try:
            if interactive_any:
                from pivot_pipeline.extract_rewrite_loop import extract_rules_with_abort_rewrite

                raw_rules = extract_rules_with_abort_rewrite(
                    nl_lines,
                    work_dir=work_dir,
                    repo_root=repo_root,
                    print_fn=print_fn,
                    input_fn=input_fn,
                )
                nl_text_for_artifacts = "\n\n".join(nl_lines) + "\n"
                (work_dir / "rules_source.txt").write_text(
                    nl_text_for_artifacts, encoding="utf-8"
                )
                if not skip_phase0:
                    npath = work_dir / "phase0_normalized_nl.txt"
                    npath.write_text(nl_text_for_artifacts, encoding="utf-8")
                    nl_for_precheck = npath
                else:
                    npath = work_dir / "nl_after_extract_rewrites.txt"
                    npath.write_text(nl_text_for_artifacts, encoding="utf-8")
                    nl_for_precheck = npath
            else:
                raw_rules = extract_rules_from_lines(nl_lines)
        except ExtractAbort as e:
            summary["outcome"] = "blocked_extraction_abort"
            summary["line_index"] = e.line_index
            summary["message"] = str(e)
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        except ExtractValidationError as e:
            summary["outcome"] = "blocked_extraction_validation"
            summary["line_index"] = e.line_index
            summary["message"] = str(e)
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        except PivotPipelineUserAbort as e:
            summary["outcome"] = "blocked_user_abort"
            summary["message"] = str(e)
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

        drop_log = work_dir / "dropped_rules_log.jsonl"
        if drop_log.is_file() and drop_log.stat().st_size > 0:
            summary["extract_dropped_rule_count"] = len(
                [ln for ln in drop_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
            )

        (work_dir / "phase1_rules_raw.json").write_text(
            json.dumps({"policy_id": policy_id, "rules": raw_rules}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        if skip_registry:
            reg_obj: dict[str, Any] = {"canonical_variables": []}
            rules = raw_rules
        else:
            try:
                reg_obj, rules = registry_pass_from_nl_and_rules(nl_lines, raw_rules)
            except Exception as e:
                summary["outcome"] = "blocked_registry"
                summary["message"] = f"registry pass failed: {e}"
                (work_dir / "run_summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return summary

        (work_dir / "identifier_registry.json").write_text(
            json.dumps(reg_obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        extracted_path = work_dir / "rules_extracted.json"
        extracted_path.write_text(
            json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        summary["rules_extracted"] = str(extracted_path.resolve())

        if extract_only:
            summary["outcome"] = "ok_extract_only"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

    nl_lines_reg = parse_nl_rules(nl_text_for_artifacts)

    def refresh_varprod_trigger_check() -> bool:
        v_issues = validate_varprod_triggers(rules, skip_rule_ids=varprod_skip_rule_ids_from_env())
        v_ok = len(v_issues) == 0
        summary["varprod_trigger_ok"] = v_ok
        summary["varprod_trigger_issues"] = v_issues
        write_ir_structure_check(work_dir, v_ok, v_issues)
        if not v_ok:
            print_fn("\n[pivot pipeline] IR structure check (varprod operands in trigger): FAILED\n")
            for it in v_issues:
                print_fn(f"  - {it}\n")
        return v_ok

    meta = None
    compile_exc: Exception | None = None
    max_struct = max(0, repairer_max_rounds)
    for s_round in range(max_struct + 1):
        try:
            meta = load_rules_and_compile(policy_id, rules)
            compile_exc = None
            break
        except Exception as e:
            compile_exc = e
            if s_round >= max_struct or no_llm:
                summary["outcome"] = "blocked_compile"
                summary["message"] = str(e)
                (work_dir / "run_summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return summary
            try:
                out, json_parse_retry_used = run_repairer_piv_structural(
                    policy_id=policy_id,
                    rules=rules,
                    error_text=str(e),
                )
            except Exception as re:
                summary["outcome"] = "blocked_compile"
                summary["message"] = f"compile failed ({e}); structural repairer failed: {re}"
                (work_dir / "run_summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return summary
            append_repairer_trace(
                work_dir,
                {
                    "round": s_round,
                    "change_summary": [c.model_dump() for c in out.change_summary],
                    "json_parse_retry_used": json_parse_retry_used,
                },
                kind="structural",
            )
            rules = out.rules
            (work_dir / "rules_after_structural_repair.json").write_text(
                json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            if not skip_registry:
                try:
                    _, rules = registry_pass_from_nl_and_rules(nl_lines_reg, rules)
                except Exception as re:
                    summary["outcome"] = "blocked_registry"
                    summary["message"] = f"after structural repair: registry failed: {re}"
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return summary
            extracted_path = work_dir / "rules_extracted.json"
            extracted_path.write_text(
                json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            summary["rules_extracted"] = str(extracted_path.resolve())

    if meta is None:
        summary["outcome"] = "blocked_compile"
        summary["message"] = str(compile_exc or "unknown compile failure")
        (work_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return summary

    meta_path = work_dir / "meta_scheme.json"
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    summary["meta_scheme"] = str(meta_path)

    z3_result = run_z3_check(meta)
    summary["z3"] = z3_result
    (work_dir / "z3_result.json").write_text(
        json.dumps(z3_result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    synth = meta_scheme_to_markdown(meta)
    synth_path = work_dir / "synthetic_en.md"
    synth_path.write_text(synth, encoding="utf-8")

    ok, issues = run_precheck(nl_path=nl_for_precheck, meta=meta)
    summary["precheck_ok"] = ok
    summary["precheck_issues"] = issues
    (work_dir / "precheck.json").write_text(
        json.dumps({"ok": ok, "issues": issues}, indent=2) + "\n",
        encoding="utf-8",
    )

    if fail_on_precheck_warnings and not ok:
        summary["outcome"] = "blocked_precheck"
        summary["message"] = "precheck reported issues (--fail-on-precheck-warnings)"
        (work_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return summary

    refresh_varprod_trigger_check()
    if fail_on_varprod_trigger and not summary.get("varprod_trigger_ok", True):
        summary["outcome"] = "blocked_varprod_trigger"
        summary["message"] = "varprod trigger IR check failed (--fail-on-varprod-trigger)"
        (work_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return summary

    if with_tester:
        try:
            z3_blob = json.dumps(z3_result, ensure_ascii=False, indent=2) if z3_result else ""
            _raw_t, tester_rep = run_pivot_tester(
                effective_nl=nl_text_for_artifacts,
                synthetic_en=synth,
                z3_summary=z3_blob[:12_000],
            )
            (work_dir / "tester_report.json").write_text(
                tester_rep.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
            summary["tester_verdict"] = tester_rep.verdict
            print_fn(format_tester_report_terminal(tester_rep))
            if tester_rep.verdict == "issues" and fail_on_tester_findings:
                summary["outcome"] = "blocked_tester"
                summary["message"] = "Tester reported issues (--fail-on-tester-findings)"
                (work_dir / "run_summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return summary
        except Exception as e:
            summary["outcome"] = "blocked_tester"
            summary["message"] = f"tester failed: {e}"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

    if skip_critic:
        summary["critic"] = "skipped"
    else:
        try:
            rules, meta, synth, z3_result, ok, issues, early = run_semantic_critic_interactive_loop(
                work_dir=work_dir,
                nl_text_for_artifacts=nl_text_for_artifacts,
                nl_for_precheck=nl_for_precheck,
                nl_lines_reg=nl_lines_reg,
                policy_id=policy_id,
                rules=rules,
                meta_path=meta_path,
                skip_registry=skip_registry,
                no_llm=no_llm,
                interactive_any=interactive_any,
                print_fn=print_fn,
                input_fn=input_fn,
                summary=summary,
                synth=synth,
                meta=meta,
                z3_result=z3_result,
                ok=ok,
                issues=issues,
            )
            if early in ("blocked_critic", "blocked_semantic_repair_compile"):
                return summary
            refresh_varprod_trigger_check()
            if fail_on_varprod_trigger and not summary.get("varprod_trigger_ok", True):
                summary["outcome"] = "blocked_varprod_trigger"
                summary["message"] = "varprod trigger IR check failed (--fail-on-varprod-trigger)"
                (work_dir / "run_summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return summary
        except Exception as e:
            summary["outcome"] = "blocked_critic"
            summary["message"] = f"critic failed: {e}"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

    if with_cross_repair and not with_cross_critic:
        summary["outcome"] = "blocked_cross_critic"
        summary["message"] = "--with-cross-repair requires --with-cross-critic"
        (work_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return summary

    if with_cross_critic:
        if no_llm:
            summary["outcome"] = "blocked_cross_critic"
            summary["message"] = "CrossCritic requires LLM calls; omit --no-llm."
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

        if not cross_coherence_skip_critic_gate:
            if skip_critic or not summary.get("critic_passed"):
                summary["outcome"] = "blocked_cross_critic"
                summary["message"] = (
                    "CrossCritic requires a passing semantic critic run first, or pass "
                    "--cross-coherence-skip-critic-gate for development."
                )
                (work_dir / "run_summary.json").write_text(
                    json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                return summary

        linearized = linearize_rules_for_cross_critic(rules)
        (work_dir / "linearized_model_for_cross_critic.txt").write_text(
            linearized, encoding="utf-8"
        )
        summary["linearized_model_for_cross_critic"] = str(
            (work_dir / "linearized_model_for_cross_critic.txt").resolve()
        )

        try:
            xc_raw, xc_report = run_cross_critic_parsed(nl_text_for_artifacts, linearized)
            (work_dir / "cross_critic_report.json").write_text(
                xc_report.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
            xc_path = work_dir / "cross_critic_result.txt"
            xc_path.write_text(xc_raw, encoding="utf-8")
            summary["cross_critic_result"] = str(xc_path.resolve())
            summary["cross_critic_verdict"] = xc_report.verdict
            print_fn(format_cross_critic_report_terminal(xc_report))

            if not cross_critic_report_ok(xc_report):
                if not interactive_cross_any:
                    summary["outcome"] = "blocked_cross_critic"
                    summary["message"] = (
                        "CrossCritic reported ISSUES; pass --interactive-policy or "
                        "--interactive-cross-coherence to choose REPAIR or PROCEED_INCOMPLETE, "
                        "or fix rules manually."
                    )
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return summary

                from pivot_pipeline.policy_gates import REPAIR_CRITIC_DRIFT_TOKEN

                cross_repairs_used = 0
                while not cross_critic_report_ok(xc_report):
                    print_fn(
                        "\n[policy gate] CrossCritic reported ISSUES.\n"
                        f"  Type {REPAIR_CRITIC_DRIFT_TOKEN!r} to run CrossRepairer from this report, then re-check "
                        "alignment with the semantic critic.\n"
                        f"  Type {PROCEED_INCOMPLETE_TOKEN!r} to continue anyway (cross coherence issues accepted).\n"
                        "  Press Enter to abort.\n"
                    )
                    ans = input_fn("> ").strip()
                    if ans == PROCEED_INCOMPLETE_TOKEN:
                        summary["cross_critic_passed"] = False
                        summary["user_consented_cross_critic_issues"] = True
                        break

                    if ans == REPAIR_CRITIC_DRIFT_TOKEN:
                        if not with_cross_repair:
                            print_fn(
                                "[policy gate] Enable --with-cross-repair to use CrossRepairer, "
                                f"or type {PROCEED_INCOMPLETE_TOKEN!r} to skip.\n"
                            )
                            continue
                        limit = cross_repair_max_rounds()
                        if cross_repairs_used >= limit:
                            print_fn(
                                f"[policy gate] Max CrossRepairer rounds ({limit}); "
                                f"type {PROCEED_INCOMPLETE_TOKEN!r} or press Enter to abort.\n"
                            )
                            continue
                        cross_repairs_used += 1
                        h = cross_critic_handoff_dict(
                            xc_report,
                            source_note="CrossRepairer from CrossCritic ISSUES",
                        )
                        try:
                            out, json_parse_retry_used = run_cross_repairer(
                                policy_id=policy_id,
                                rules=rules,
                                handoff=h,
                                processed_nl_excerpt=nl_text_for_artifacts,
                                linearized_excerpt=linearized,
                            )
                        except Exception as re:
                            print_fn(f"[policy gate] CrossRepairer failed: {re}\n")
                            continue
                        append_cross_repairer_trace(
                            work_dir,
                            {
                                "round": cross_repairs_used,
                                "change_summary": [c.model_dump() for c in out.change_summary],
                                "json_parse_retry_used": json_parse_retry_used,
                            },
                        )
                        new_rules = out.rules
                        if not skip_registry:
                            try:
                                _, new_rules = registry_pass_from_nl_and_rules(nl_lines_reg, new_rules)
                            except Exception as re:
                                print_fn(f"[policy gate] Registry after cross repair failed: {re}\n")
                                continue
                        try:
                            meta = load_rules_and_compile(policy_id, new_rules)
                        except Exception as ce:
                            print_fn(f"[policy gate] Cross-repaired rules did not compile: {ce}\n")
                            continue
                        rules = new_rules
                        extracted_path = work_dir / "rules_extracted.json"
                        extracted_path.write_text(
                            json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False)
                            + "\n",
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
                        (work_dir / "rules_after_cross_repair.json").write_text(
                            json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False)
                            + "\n",
                            encoding="utf-8",
                        )
                        linearized = linearize_rules_for_cross_critic(rules)
                        (work_dir / "linearized_model_for_cross_critic.txt").write_text(
                            linearized, encoding="utf-8"
                        )

                        try:
                            rules, meta, synth, z3_result, ok, issues, early = (
                                run_semantic_critic_interactive_loop(
                                    work_dir=work_dir,
                                    nl_text_for_artifacts=nl_text_for_artifacts,
                                    nl_for_precheck=nl_for_precheck,
                                    nl_lines_reg=nl_lines_reg,
                                    policy_id=policy_id,
                                    rules=rules,
                                    meta_path=meta_path,
                                    skip_registry=skip_registry,
                                    no_llm=no_llm,
                                    interactive_any=interactive_cross_any,
                                    print_fn=print_fn,
                                    input_fn=input_fn,
                                    summary=summary,
                                    synth=synth,
                                    meta=meta,
                                    z3_result=z3_result,
                                    ok=ok,
                                    issues=issues,
                                )
                            )
                        except Exception as e:
                            summary["outcome"] = "blocked_post_cross_critic"
                            summary["message"] = f"post cross-repair semantic critic failed: {e}"
                            (work_dir / "run_summary.json").write_text(
                                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8",
                            )
                            return summary
                        if early in ("blocked_critic", "blocked_semantic_repair_compile"):
                            summary["outcome"] = summary.get("outcome") or "blocked_post_cross_critic"
                            return summary

                        summary["post_cross_repair_critic_done"] = True
                        xc_raw, xc_report = run_cross_critic_parsed(nl_text_for_artifacts, linearized)
                        (work_dir / "cross_critic_report.json").write_text(
                            xc_report.model_dump_json(indent=2) + "\n",
                            encoding="utf-8",
                        )
                        (work_dir / "cross_critic_result.txt").write_text(xc_raw, encoding="utf-8")
                        summary["cross_critic_verdict"] = xc_report.verdict
                        print_fn(format_cross_critic_report_terminal(xc_report))
                        if cross_critic_report_ok(xc_report):
                            summary["cross_critic_passed"] = True
                        continue

                    summary["outcome"] = "blocked_cross_critic"
                    (work_dir / "run_summary.json").write_text(
                        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    return summary
            else:
                summary["cross_critic_passed"] = True
        except Exception as e:
            summary["outcome"] = "blocked_cross_critic"
            summary["message"] = f"cross critic failed: {e}"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

    if with_cross_critic:
        refresh_varprod_trigger_check()
        if fail_on_varprod_trigger and not summary.get("varprod_trigger_ok", True):
            summary["outcome"] = "blocked_varprod_trigger"
            summary["message"] = "varprod trigger IR check failed after cross-coherence (--fail-on-varprod-trigger)"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

    if with_cross_critic and not skip_critic and summary.get("cross_critic_passed"):
        print_fn(
            "\n[pivot pipeline] CrossCritic passed — running semantic critic again as the final "
            "NL ↔ synthetic alignment check.\n"
        )
        try:
            rules, meta, synth, z3_result, ok, issues, early = run_semantic_critic_interactive_loop(
                work_dir=work_dir,
                nl_text_for_artifacts=nl_text_for_artifacts,
                nl_for_precheck=nl_for_precheck,
                nl_lines_reg=nl_lines_reg,
                policy_id=policy_id,
                rules=rules,
                meta_path=meta_path,
                skip_registry=skip_registry,
                no_llm=no_llm,
                interactive_any=interactive_any or interactive_cross_any,
                print_fn=print_fn,
                input_fn=input_fn,
                summary=summary,
                synth=synth,
                meta=meta,
                z3_result=z3_result,
                ok=ok,
                issues=issues,
            )
            if early in ("blocked_critic", "blocked_semantic_repair_compile"):
                return summary
        except Exception as e:
            summary["outcome"] = "blocked_critic"
            summary["message"] = f"post-CrossCritic semantic critic failed: {e}"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary
        summary["post_cross_semantic_critic_final"] = True
        refresh_varprod_trigger_check()
        if fail_on_varprod_trigger and not summary.get("varprod_trigger_ok", True):
            summary["outcome"] = "blocked_varprod_trigger"
            summary["message"] = "varprod trigger IR check failed after final semantic (--fail-on-varprod-trigger)"
            (work_dir / "run_summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return summary

    if with_template_generator or template_suite_path is not None:
        path_to_run: Path | None = None
        if with_template_generator and not no_llm:
            try:
                from pivot_pipeline.template_generator_agent import run_template_generator_pipeline

                path_to_run = run_template_generator_pipeline(work_dir=work_dir)
                summary["template_suite_path"] = str(path_to_run.resolve())
                summary["template_suite_source"] = "generated"
            except Exception as e:
                summary["template_suite_ok"] = False
                summary["template_suite_error"] = f"{type(e).__name__}: {e}"
                print_fn(f"[template_suite] generator failed (non-fatal): {e}", file=sys.stderr)
        elif with_template_generator and no_llm:
            summary["template_suite_generator_skipped"] = "no_llm"
            print_fn(
                "[template_suite] generator skipped: --no-llm (use --template-suite to run a file).",
                file=sys.stderr,
            )

        if path_to_run is None and template_suite_path is not None:
            cand = template_suite_path.resolve()
            path_to_run = cand
            summary["template_suite_path"] = str(cand)
            if summary.get("template_suite_source") != "generated":
                summary["template_suite_source"] = "file"

        if path_to_run is not None:
            if not path_to_run.is_file():
                summary["template_suite_ok"] = False
                summary["template_suite_error"] = f"missing suite file: {path_to_run}"
                print_fn(f"[template_suite] {summary['template_suite_error']}", file=sys.stderr)
            else:
                try:
                    from pivot_pipeline.template_suite.run import run_template_suite

                    trep = run_template_suite(
                        suite_path=path_to_run,
                        rules_extracted_path=work_dir / "rules_extracted.json",
                        out_report_path=work_dir / "template_run_report.json",
                        write_report=True,
                    )
                    summary["template_suite_summary"] = trep["summary"]
                    summary["template_run_report"] = str((work_dir / "template_run_report.json").resolve())
                    summary["template_suite_ok"] = True
                    summary.pop("template_suite_error", None)
                    print_fn(
                        f"[template_suite] verdicts: passed={trep['summary']['passed']} "
                        f"failed={trep['summary']['failed']} errors={trep['summary']['errors']} "
                        f"inconclusive={trep['summary']['inconclusive']}"
                    )
                except Exception as e:
                    summary["template_suite_ok"] = False
                    summary["template_suite_error"] = f"{type(e).__name__}: {e}"
                    print_fn(f"[template_suite] run failed (non-fatal): {e}", file=sys.stderr)

    warnings: list[str] = []
    if summary.get("user_consented_wfm_incomplete_coverage"):
        warnings.append("wfm_fewer_rules_than_source_accepted")
    if summary.get("extract_dropped_rule_count"):
        warnings.append("extract_dropped_rules")
    if summary.get("user_consented_cross_critic_issues"):
        warnings.append("cross_critic_issues_accepted")
    if summary.get("user_consented_critic_drift"):
        warnings.append("critic_drift_accepted")
    if summary.get("varprod_trigger_ok") is False:
        warnings.append("varprod_trigger_ir_mismatch")
    if warnings:
        summary["policy_incomplete_consents"] = warnings

    precheck_bad = not ok
    varprod_bad = summary.get("varprod_trigger_ok") is False
    if precheck_bad and varprod_bad:
        summary["outcome"] = "precheck_ir_structure_warnings"
    elif varprod_bad:
        summary["outcome"] = "ir_structure_warnings"
    elif precheck_bad:
        summary["outcome"] = "precheck_warnings"
    else:
        summary["outcome"] = "ok"
    (work_dir / "run_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary
