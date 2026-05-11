"""CLI: run / validate-domain / runtime-check / prepare-from-wfm (slice 7)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

from cpmpy_wfm_policy.llm.gemini_client import gemini_formalizer_llm
from cpmpy_wfm_policy.pipeline.ast_validator import load_signature_namespace
from cpmpy_wfm_policy.pipeline.domain_inputs import (
    gated_tool_names,
    load_tool_dependencies_from_signature,
    load_tools_json_file,
    validate_domain_dir_layout,
)
from cpmpy_wfm_policy.pipeline.orchestrator import run_orchestrator
from cpmpy_wfm_policy.runtime.audit_log import append_audit_jsonl, audit_record_from_decision
from cpmpy_wfm_policy.runtime.router import gate_tool
from cpmpy_wfm_policy.wfm_import.adapter import materialize_domain_bundle_from_handoff
from cpmpy_wfm_policy.pipeline.reset_domain_bundle import reset_domain_for_rerun
from cpmpy_wfm_policy.pipeline.drafting import (
    Phase0Config,
    check_glossary_file,
    check_signature_file,
    run_phase0,
)


def cmd_validate_domain(domain: Path) -> int:
    problems = validate_domain_dir_layout(domain)
    if problems:
        for prob in problems:
            print(prob, file=sys.stderr)
        return 1
    try:
        tools = load_tools_json_file(domain / "tools.json")
        load_tool_dependencies_from_signature(domain / "signature.py")
    except Exception as e:
        print(f"validation error: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "gated_tools": gated_tool_names(tools)}, indent=2))
    return 0


def cmd_prepare_from_wfm(handoff: Path, out_dir: Path, include_all: bool) -> int:
    try:
        materialize_domain_bundle_from_handoff(
            handoff_path=handoff,
            out_dir=out_dir,
            pass_only=not include_all,
        )
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "out_dir": str(out_dir.resolve())}))
    return 0


def cmd_run(domain: Path, out_dir: Path) -> int:
    try:
        llm = gemini_formalizer_llm()
    except Exception as e:
        print(f"LLM not configured: {e}", file=sys.stderr)
        return 1
    res = run_orchestrator(domain_dir=domain, out_dir=out_dir, formalizer_llm=llm)
    if not res.success:
        print(res.error or "failed", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "out_dir": str(res.out_dir.resolve())}))
    return 0


def cmd_runtime_check(bundle_dir: Path, pattern_b_solver: str = "z3") -> int:
    pol = bundle_dir / "policy.py"
    man_path = bundle_dir / "manifest.json"
    sig_path = bundle_dir / "signature.py"
    for p in (pol, man_path, sig_path):
        if not p.is_file():
            print(f"missing {p}", file=sys.stderr)
            return 1
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    policy_version = str(manifest.get("policy_version", ""))

    spec = importlib.util.spec_from_file_location("_orch_policy", pol)
    if spec is None or spec.loader is None:
        print("cannot load policy.py", file=sys.stderr)
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rules = mod.all_rules()
    ns = load_signature_namespace(sig_path)
    deps = load_tool_dependencies_from_signature(sig_path)
    tool_names = list(deps.keys())
    if not tool_names:
        print("no TOOL_DEPENDENCIES in signature", file=sys.stderr)
        return 1

    tname = tool_names[0]
    dep_names = deps[tname]
    state: dict[str, int | bool] = {}
    for nm in dep_names:
        v = ns.get(nm)
        if v is None:
            continue
        shape = getattr(v, "shape", None)
        if shape is not None:
            shp_t = shape if isinstance(shape, tuple) else (shape,)
            if len(shp_t) == 1:
                for i in range(int(shp_t[0])):
                    state[f"{nm}[{i}]"] = 0
        else:
            if hasattr(v, "lb"):
                lo, hi = int(v.lb), int(v.ub)
                state[nm] = bool(lo) if lo == hi and (lo in (0, 1)) else lo
            else:
                state[nm] = 0

    decision = gate_tool(
        all_rules=rules,
        manifest=manifest,
        state=state,
        signature_namespace=ns,
        pattern_b_solver=pattern_b_solver,
    )
    rec = audit_record_from_decision(
        policy_version=policy_version or "unknown",
        tool_call={"name": tname, "parameters": {}},
        state_snapshot=state,
        manifest=manifest,
        decision=decision,
    )
    log_path = bundle_dir / "runtime_audit.jsonl"
    append_audit_jsonl(log_path, rec)
    print(json.dumps({"ok": True, "decision": rec.to_jsonable(), "audit_log": str(log_path)}))
    return 0


def cmd_phase0_check_signature(domain: Path, report_out: Path | None) -> int:
    t = domain / "tools.json"
    rep = check_signature_file(
        domain / "signature.py",
        tools_json_path=t if t.is_file() else None,
        require_tools_json_alignment=t.is_file(),
    )
    if report_out is not None:
        rep.write_json(report_out)
    print(json.dumps(rep.to_jsonable(), indent=2))
    return 0 if rep.pass_ else 1


def cmd_phase0_check_glossary(domain: Path, report_out: Path | None) -> int:
    rules_path = domain / "rules.txt"
    notes_path = domain / "domain_notes.md"
    rules_text = rules_path.read_text(encoding="utf-8") if rules_path.is_file() else None
    domain_notes = notes_path.read_text(encoding="utf-8") if notes_path.is_file() else None
    rep = check_glossary_file(
        domain / "glossary.md",
        signature_path=domain / "signature.py",
        rules_text=rules_text,
        domain_notes=domain_notes,
        inferred_phrase_symbols=None,
    )
    if report_out is not None:
        rep.write_json(report_out)
    print(json.dumps(rep.to_jsonable(), indent=2))
    return 0 if rep.pass_ else 1


def cmd_phase0_run(domain: Path, *, skip_human: bool, rerun_phase_0a: bool) -> int:
    try:
        llm = gemini_formalizer_llm()
    except Exception as e:
        print(f"LLM not configured: {e}", file=sys.stderr)
        return 1
    res = run_phase0(
        domain,
        llm=llm,
        cfg=Phase0Config(skip_human=skip_human, rerun_phase_0a=rerun_phase_0a),
    )
    out = {
        "ok": res.success,
        "phase_0a_complete": res.phase_0a_complete,
        "phase_0b_complete": res.phase_0b_complete,
        "error": res.error,
        "domain_dir": str(domain.resolve()),
    }
    print(json.dumps(out, indent=2))
    return 0 if res.success else 1


def cmd_reset_domain(domain: Path, out_dir: Path | None) -> int:
    payload = reset_domain_for_rerun(domain, out_dir=out_dir)
    print(json.dumps({"ok": True, **payload}, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="cpmpy-policy-pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate-domain", help="Check domain bundle layout + tools.json")
    v.add_argument("--domain", type=Path, required=True)

    pr = sub.add_parser("prepare-from-wfm", help="Materialize rules.txt + stub tools.json")
    pr.add_argument("--handoff", type=Path, required=True)
    pr.add_argument("--out-dir", type=Path, required=True)
    pr.add_argument("--include-all-verdicts", action="store_true")

    r = sub.add_parser("run", help="Run orchestrator with Gemini from env (live LLM)")
    r.add_argument("--domain", type=Path, required=True)
    r.add_argument("--out-dir", type=Path, required=True)

    rt = sub.add_parser("runtime-check", help="Smoke gate_tool + audit log line")
    rt.add_argument(
        "--bundle-dir",
        type=Path,
        required=True,
        help="Directory with policy.py, manifest.json, signature.py",
    )
    rt.add_argument("--pattern-b-solver", default="z3")

    p0s = sub.add_parser("phase0-check-signature", help="Structural check signature.py (+ tools.json if present)")
    p0s.add_argument("--domain", type=Path, required=True)
    p0s.add_argument("--report-out", type=Path, default=None)

    p0g = sub.add_parser("phase0-check-glossary", help="Structural check glossary.md (uses rules.txt / domain_notes.md if present)")
    p0g.add_argument("--domain", type=Path, required=True)
    p0g.add_argument("--report-out", type=Path, default=None)

    p0r = sub.add_parser("phase0-run", help="Run Phase 0 drafter/critic/refiner/glossary (requires LLM env)")
    p0r.add_argument("--domain", type=Path, required=True)
    p0r.add_argument("--skip-human", action="store_true", help="Skip blocking on human review gate file")
    p0r.add_argument("--rerun-phase-0a", action="store_true", help="Re-run signature loop even if artifacts exist")

    rz = sub.add_parser(
        "reset-domain",
        help="Delete Phase 0 generated files under --domain; optionally wipe --out-dir for a clean rerun",
    )
    rz.add_argument("--domain", type=Path, required=True)
    rz.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="If set, remove this directory entirely and recreate it empty (orchestrator output)",
    )

    args = p.parse_args(argv)
    if args.cmd == "validate-domain":
        return cmd_validate_domain(args.domain)
    if args.cmd == "prepare-from-wfm":
        return cmd_prepare_from_wfm(args.handoff, args.out_dir, args.include_all_verdicts)
    if args.cmd == "run":
        return cmd_run(args.domain, args.out_dir)
    if args.cmd == "runtime-check":
        return cmd_runtime_check(args.bundle_dir, args.pattern_b_solver)
    if args.cmd == "phase0-check-signature":
        return cmd_phase0_check_signature(args.domain, args.report_out)
    if args.cmd == "phase0-check-glossary":
        return cmd_phase0_check_glossary(args.domain, args.report_out)
    if args.cmd == "phase0-run":
        return cmd_phase0_run(
            args.domain,
            skip_human=args.skip_human,
            rerun_phase_0a=args.rerun_phase_0a,
        )
    if args.cmd == "reset-domain":
        return cmd_reset_domain(args.domain, args.out_dir)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
