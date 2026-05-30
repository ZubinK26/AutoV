"""CLI entry to run Template Diagnostician + Repairer on an existing work directory."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Default Pro model for one-off template repair runs (--gemini-pro).
_TEMPLATE_REPAIR_GEMINI_PRO_DEFAULT = "gemini-3.1-pro-preview"

_REPO = Path(__file__).resolve().parents[2]


def _resolve_nl_for_work_dir(work_dir: Path, nl_source: Path) -> tuple[Path, str]:
    for name in (
        "nl_after_extract_rewrites.txt",
        "phase0_normalized_nl.txt",
        "rules_source.txt",
    ):
        p = work_dir / name
        if p.is_file() and p.stat().st_size > 0:
            return p.resolve(), p.read_text(encoding="utf-8")
    p = nl_source.resolve()
    return p, p.read_text(encoding="utf-8")


def _load_work_dir_state(
    work_dir: Path,
    *,
    nl_source: Path,
    rules_json: Path,
    suite_path: Path | None,
) -> dict[str, Any]:
    from pivot_pipeline.ir import MetaScheme, load_rules_and_compile
    from wfm_orchestration.nl_chunk_policy_pipeline import parse_nl_rules
    from pivot_pipeline.rules_document import parse_rules_document

    report_path = work_dir / "template_run_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(
            f"missing {report_path}; run template suite first (pivot-pipeline --with-template-generator "
            "or pivot-template-suite)."
        )

    nl_for_precheck, nl_text = _resolve_nl_for_work_dir(work_dir, nl_source)
    policy_id, rules, envelope = parse_rules_document(
        json.loads(rules_json.read_text(encoding="utf-8"))
    )
    meta_path = work_dir / "meta_scheme.json"
    if meta_path.is_file():
        meta = MetaScheme.model_validate_json(meta_path.read_text(encoding="utf-8"))
    else:
        meta = load_rules_and_compile(
            policy_id,
            rules,
            policy_semantics_version=envelope.get("policy_semantics_version"),
        )
        meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")

    synth_path = work_dir / "synthetic_en.md"
    synth = synth_path.read_text(encoding="utf-8") if synth_path.is_file() else ""

    z3_path = work_dir / "z3_result.json"
    z3_result: dict[str, Any] = {}
    if z3_path.is_file():
        z3_result = json.loads(z3_path.read_text(encoding="utf-8"))

    pre_path = work_dir / "precheck.json"
    ok, issues = True, []
    if pre_path.is_file():
        pre = json.loads(pre_path.read_text(encoding="utf-8"))
        ok = bool(pre.get("ok", True))
        issues = pre.get("issues") or []

    lin_path = work_dir / "linearized_model_for_assessment.txt"
    linearized = lin_path.read_text(encoding="utf-8") if lin_path.is_file() else None

    if suite_path is None:
        handoff = work_dir / "template_repair_handoff.json"
        if handoff.is_file():
            h = json.loads(handoff.read_text(encoding="utf-8"))
            sp = h.get("suite_path")
            if sp:
                suite_path = Path(sp)
        if suite_path is None:
            gen = work_dir / "template_suite_generated.json"
            suite_path = gen if gen.is_file() else None

    if suite_path is None or not suite_path.is_file():
        raise FileNotFoundError(
            "no template suite JSON found; pass --template-suite or run template generator first."
        )

    summary: dict[str, Any] = {"template_run_report": str(report_path.resolve())}
    if envelope:
        summary.update({k: envelope[k] for k in ("policy_semantics_version", "pivot_ir_extensions") if k in envelope})

    return {
        "policy_id": policy_id,
        "rules": rules,
        "meta": meta,
        "meta_path": meta_path,
        "nl_for_precheck": nl_for_precheck,
        "nl_text_for_artifacts": nl_text,
        "nl_lines_reg": parse_nl_rules(nl_text),
        "synth": synth,
        "z3_result": z3_result,
        "ok": ok,
        "issues": issues,
        "linearized": linearized,
        "suite_path": suite_path.resolve(),
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Run Template Diagnostician + interactive Template Repairer on an existing pivot work "
            "directory that already has template_run_report.json with fail/inconclusive tests. "
            "Does not run WFM, extract, or full pivot-pipeline."
        ),
        epilog=(
            "Example:\n"
            "  pivot-template-repair --work-dir NagV/exports/pivot_runs/Backend_Engineer2_v1_wfm "
            "--input path/to/latest.nl --interactive-template-suite\n\n"
            "  One run with Gemini Pro (does not change global env after exit):\n"
            "  python -m pivot_pipeline.run_template_repair ... --interactive-template-suite "
            "--gemini-pro\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--work-dir", required=True, type=Path)
    p.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Original nl_source path (policy id); same as pivot-pipeline CLI",
    )
    p.add_argument(
        "--rules-json",
        type=Path,
        default=None,
        help="Defaults to <work-dir>/rules_extracted.json",
    )
    p.add_argument(
        "--template-suite",
        type=Path,
        default=None,
        help="Defaults to handoff suite_path or <work-dir>/template_suite_generated.json",
    )
    p.add_argument("--repo-root", type=Path, default=_REPO)
    p.add_argument(
        "--interactive-template-suite",
        action="store_true",
        help="Enable triage + REPAIR / PROCEED_INCOMPLETE gate (required for repair).",
    )
    p.add_argument(
        "--interactive-policy",
        action="store_true",
        help="Same as pivot-pipeline: enables template repair gate.",
    )
    p.add_argument(
        "--reverify-tester",
        action="store_true",
        help="After repair, re-run Pivot Tester (requires LLM).",
    )
    p.add_argument(
        "--reverify-critic",
        action="store_true",
        help="After repair, re-run semantic critic (requires LLM).",
    )
    p.add_argument(
        "--reverify-cross",
        action="store_true",
        help="After repair, re-run CrossCritic when cross_critic_report.json exists.",
    )
    p.add_argument("--skip-registry", action="store_true")
    p.add_argument("--no-llm", action="store_true", help="Template repair requires LLM; rejected")
    p.add_argument("--no-vnext-lowering", action="store_true")
    p.add_argument(
        "--gemini-model",
        type=str,
        default=None,
        metavar="MODEL",
        help=(
            "Override PIVOT_GEMINI_MODEL for this process only (diagnostician + repairer + "
            "optional reverify LLM steps)."
        ),
    )
    p.add_argument(
        "--gemini-thinking-level",
        type=str,
        default=None,
        metavar="LEVEL",
        help="Override PIVOT_GEMINI_THINKING_LEVEL for this process only (e.g. low, medium, high).",
    )
    p.add_argument(
        "--gemini-pro",
        action="store_true",
        help=f"Shorthand for --gemini-model {_TEMPLATE_REPAIR_GEMINI_PRO_DEFAULT!r}.",
    )
    args = p.parse_args(argv)

    if args.gemini_pro and args.gemini_model:
        print("error: use only one of --gemini-pro and --gemini-model", file=sys.stderr)
        return 2
    model_override = args.gemini_model or (
        _TEMPLATE_REPAIR_GEMINI_PRO_DEFAULT if args.gemini_pro else None
    )
    if model_override:
        os.environ["PIVOT_GEMINI_MODEL"] = model_override.strip()
    if args.gemini_thinking_level:
        os.environ["PIVOT_GEMINI_THINKING_LEVEL"] = args.gemini_thinking_level.strip()
    if model_override or args.gemini_thinking_level:
        from pivot_pipeline.llm import (
            get_pivot_gemini_model,
            get_pivot_gemini_thinking_level_str,
        )

        print(
            f"[template_repair] Gemini for this run: model={get_pivot_gemini_model()!r} "
            f"thinking_level={get_pivot_gemini_thinking_level_str()!r}\n"
        )

    if args.no_llm:
        print("error: Template repair requires LLM calls; omit --no-llm.", file=sys.stderr)
        return 1
    if not args.interactive_template_suite and not args.interactive_policy:
        print(
            "error: pivot-template-repair requires --interactive-template-suite or --interactive-policy",
            file=sys.stderr,
        )
        return 1

    rules_json = args.rules_json or (args.work_dir / "rules_extracted.json")
    if not rules_json.is_file():
        print(f"rules JSON not found: {rules_json}", file=sys.stderr)
        return 1

    from pivot_pipeline.exceptions import PivotPipelineUserAbort
    from pivot_pipeline.paths import resolve_existing_user_file
    from pivot_pipeline.template_interactive_loop import run_template_interactive_loop

    nl_source = resolve_existing_user_file(args.input)
    work_dir = args.work_dir.resolve()

    try:
        st = _load_work_dir_state(
            work_dir,
            nl_source=nl_source,
            rules_json=rules_json,
            suite_path=args.template_suite,
        )
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    reverify_cross = args.reverify_cross and (work_dir / "cross_critic_report.json").is_file()

    try:
        rules, meta, synth, z3_result, ok, issues, linearized, early = run_template_interactive_loop(
            work_dir=work_dir,
            nl_text_for_artifacts=st["nl_text_for_artifacts"],
            nl_for_precheck=st["nl_for_precheck"],
            nl_lines_reg=st["nl_lines_reg"],
            policy_id=st["policy_id"],
            rules=st["rules"],
            meta_path=st["meta_path"],
            skip_registry=args.skip_registry,
            no_llm=False,
            skip_vnext_lowering=args.no_vnext_lowering,
            interactive_any=args.interactive_policy or args.interactive_template_suite,
            with_template_repair=True,
            suite_path=st["suite_path"],
            reverify_tester=args.reverify_tester,
            reverify_critic=args.reverify_critic,
            reverify_cross=reverify_cross,
            skip_critic=not args.reverify_critic,
            with_cross_critic=reverify_cross,
            print_fn=print,
            input_fn=input,
            summary=st["summary"],
            synth=st["synth"],
            meta=st["meta"],
            z3_result=st["z3_result"],
            ok=st["ok"],
            issues=st["issues"],
            linearized=st["linearized"],
        )
    except PivotPipelineUserAbort as e:
        st["summary"]["outcome"] = "aborted"
        st["summary"]["message"] = str(e)
        print(json.dumps(st["summary"], indent=2, ensure_ascii=False))
        return 1

    st["summary"]["outcome"] = early or "ok"
    print(json.dumps(st["summary"], indent=2, ensure_ascii=False))
    if early == "blocked_template_diagnostic":
        return 1
    if early == "blocked_template_repair_compile":
        return 3
    if early:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
