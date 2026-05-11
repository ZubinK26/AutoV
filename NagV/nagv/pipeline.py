"""NagV orchestration: WFM → Z3 feasibility gate → semantic critic → Z3 verify (sat)."""

from __future__ import annotations

import json
import shutil
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from nagv.agent_trace import configure_agent_trace
from nagv.critic_agent import critique
from nagv.formalizer_agent import formalize
from nagv.prompt_build import critic_passed, is_abort_response
from nagv.repair_agent import repair_code
from nagv.syntax_check import syntax_errors
from nagv.wfm_phase import aggregate_wfm_nl_for_nagv, run_wfm_until_complete
from nagv.z3_runner import Z3Result, format_z3_diagnostic, run_z3, z3_feasibility_passed

# Shared pool for Phase B (Z3 feasibility repairs) and Phase D (post–semantic verify repairs).
Z3_REPAIR_CAP = 10
Z3_REPAIR_FINAL_FLOOR = 2

SEMANTIC_ROUNDS = 5
SEMANTIC_INNER_CAP = 5

SYNTAX_INNER_CAP = 5
Z3_INNER_CAP = 5


@dataclass
class SolverRepairBudget:
    """Repairs before semantic PASS may use at most ``cap - floor``; Phase D uses remaining."""

    cap: int
    floor: int
    used: int = 0
    semantic_phase_complete: bool = False

    def mark_semantic_complete(self) -> None:
        self.semantic_phase_complete = True

    def can_repair_phase_b(self) -> bool:
        if self.semantic_phase_complete:
            return False
        return self.used < self.cap - self.floor

    def can_repair_phase_d(self) -> bool:
        return self.used < self.cap

    def spend(self, n: int = 1) -> None:
        self.used += n


@dataclass
class NagvRunResult:
    outcome: str
    message: str
    work_dir: Path
    final_py: Path | None = None
    detail: dict[str, Any] = field(default_factory=dict)


def _save_json(path: Path, d: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _merge_nagv_progress(work_dir: Path, patch: dict[str, Any]) -> None:
    p = work_dir / "nagv_progress.json"
    prev: dict[str, Any] = {}
    if p.is_file():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    prev.update(patch)
    _save_json(p, prev)


def finalize_run(result: NagvRunResult) -> NagvRunResult:
    """Write ``run_summary.json`` and update ``nagv_progress.json`` markers."""
    summary: dict[str, Any] = {
        "outcome": result.outcome,
        "message": result.message,
        **result.detail,
    }
    if result.final_py:
        summary["final_py"] = str(result.final_py)
    _save_json(result.work_dir / "run_summary.json", summary)
    _merge_nagv_progress(
        result.work_dir,
        {"last_outcome": result.outcome, "last_message": result.message},
    )
    return result


def _write_verification_log(work_dir: Path, z: Z3Result) -> None:
    log_path = work_dir / "verification_log.txt"
    extra = ""
    if z.payload:
        extra = f"\n--- payload ---\n{json.dumps(z.payload, indent=2, ensure_ascii=False)[:12000]}\n"
    log_path.write_text(
        f"kind={z.kind} ok={z.ok} z3_status={z.z3_status} exit={z.exit_code}\n"
        f"feasibility_ok={z.feasibility_ok} unsat_core={z.unsat_core}\n"
        f"--- stdout ---\n{z.stdout}\n--- stderr ---\n{z.stderr}{extra}",
        encoding="utf-8",
    )


def produce_initial_syntax_ok_code(
    *,
    nl: str,
    candidates_dir: Path,
    tag: str,
    print_fn: Callable[..., None],
) -> tuple[str | None, str]:
    """Formalizer → syntax repair only (no Z3, no critic)."""
    candidates_dir.mkdir(parents=True, exist_ok=True)
    code: str | None = None
    last_syntax: str = ""

    for attempt in range(SYNTAX_INNER_CAP):
        prefix = f"{tag}_syn{attempt:02d}"
        try:
            if attempt == 0:
                code, raw_f = formalize(nl, "", trace_step=f"{prefix}_formalizer")
                (candidates_dir / f"{prefix}_formalizer_raw.txt").write_text(raw_f, encoding="utf-8")
            else:
                if not last_syntax.strip() or code is None:
                    return None, "inner_syntax_bug"
                code, raw_f = repair_code(
                    nl_ruleset=nl,
                    current_python=code,
                    diagnostic=last_syntax.strip(),
                    trace_step=f"{prefix}_repair",
                )
                (candidates_dir / f"{prefix}_repair_raw.txt").write_text(raw_f, encoding="utf-8")
        except Exception as e:
            agent = "repair" if attempt > 0 else "formalizer"
            print_fn(f"[{prefix}] {agent} API error: {e}", file=sys.stderr)
            return None, f"error_api: {e}"

        if code is None:
            return None, "out_of_scope"
        (candidates_dir / f"{prefix}_candidate.py").write_text(code, encoding="utf-8")
        se = syntax_errors(code)
        if not se:
            return code, "ok"
        last_syntax = f"Python syntax error from ast.parse: {se}"
    return None, "rejected_syntax_inner"


def solver_repair_only_align(
    *,
    nl: str,
    repair_bootstrap: tuple[str, str],
    candidates_dir: Path,
    tag: str,
    budget: SolverRepairBudget,
    phase: Literal["b", "d"],
    print_fn: Callable[..., None],
) -> tuple[str | None, str]:
    """Repair from Z3 / tool diagnostic only (no critic). Counts ``budget.spend`` per repair attempt."""
    candidates_dir.mkdir(parents=True, exist_ok=True)
    bc_code, bc_diag = repair_bootstrap
    code: str | None = bc_code
    last_error = bc_diag.strip()

    for attempt in range(Z3_INNER_CAP):
        prefix = f"{tag}_{attempt:02d}"
        can = budget.can_repair_phase_b() if phase == "b" else budget.can_repair_phase_d()
        if not can:
            return None, "solver_repair_budget_exhausted"

        try:
            if attempt == 0:
                code, raw_f = repair_code(
                    nl_ruleset=nl,
                    current_python=bc_code,
                    diagnostic=last_error,
                    trace_step=f"{prefix}_repair_bootstrap",
                )
                (candidates_dir / f"{prefix}_repair_raw.txt").write_text(raw_f, encoding="utf-8")
            else:
                if not last_error.strip() or code is None:
                    return None, "inner_solver_align_bug"
                ec = code
                code, raw_f = repair_code(
                    nl_ruleset=nl,
                    current_python=ec,
                    diagnostic=last_error.strip(),
                    trace_step=f"{prefix}_repair",
                )
                (candidates_dir / f"{prefix}_repair_raw.txt").write_text(raw_f, encoding="utf-8")
        except Exception as e:
            print_fn(f"[{prefix}] repair API error: {e}", file=sys.stderr)
            return None, f"error_api: {e}"

        budget.spend(1)

        if code is None:
            return None, "out_of_scope"
        (candidates_dir / f"{prefix}_candidate.py").write_text(code, encoding="utf-8")
        se = syntax_errors(code)
        if se:
            last_error = f"Python syntax error from ast.parse: {se}"
            continue
        return code, "repaired"

    return None, "inner_solver_repair_exhausted"


def semantic_repair_align(
    *,
    nl: str,
    code: str,
    candidates_dir: Path,
    tag: str,
    print_fn: Callable[..., None],
) -> tuple[str | None, str]:
    """Critic then repair on critic/syntax feedback (after Z3 feasibility gate)."""
    candidates_dir.mkdir(parents=True, exist_ok=True)
    cur = code
    last_error: str = ""

    for attempt in range(SEMANTIC_INNER_CAP):
        prefix = f"{tag}_{attempt:02d}"
        try:
            if attempt == 0:
                raw_c = critique(nl_ruleset=nl, python_code=cur, trace_step=f"{prefix}_critic")
            else:
                if not last_error.strip():
                    return None, "inner_semantic_bug"
                cur2, raw_f = repair_code(
                    nl_ruleset=nl,
                    current_python=cur,
                    diagnostic=last_error.strip(),
                    trace_step=f"{prefix}_repair",
                )
                (candidates_dir / f"{prefix}_repair_raw.txt").write_text(raw_f, encoding="utf-8")
                if cur2 is None:
                    return None, "out_of_scope"
                cur = cur2
                (candidates_dir / f"{prefix}_candidate.py").write_text(cur, encoding="utf-8")
                se = syntax_errors(cur)
                if se:
                    last_error = f"Python syntax error from ast.parse: {se}"
                    continue
                raw_c = critique(nl_ruleset=nl, python_code=cur, trace_step=f"{prefix}_critic")
        except Exception as e:
            print_fn(f"[{prefix}] semantic API error: {e}", file=sys.stderr)
            return None, f"error_api: {e}"

        (candidates_dir / f"{prefix}_critic.txt").write_text(raw_c, encoding="utf-8")
        if critic_passed(raw_c):
            return cur, "aligned"
        last_error = raw_c.strip()

    return None, "inner_semantic_exhausted"


def run_nagv(
    *,
    repo_root: Path,
    nl_file: Path | None,
    work_dir: Path,
    skip_wfm: bool,
    rules_per_chunk: int,
    reset_wfm_progress: bool,
    solver_timeout_sec: int,
    print_fn: Callable[..., None] = print,
) -> NagvRunResult:
    from nagv.runtime_env import apply_nagv_gemini_defaults, apply_nagv_gemini_post_wfm_thinking

    apply_nagv_gemini_defaults()
    try:
        from wfm_orchestration.e2e_context import load_dotenv_for_e2e

        load_dotenv_for_e2e()
    except Exception:
        pass

    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    configure_agent_trace(work_dir)
    candidates_root = work_dir / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)

    budget = SolverRepairBudget(Z3_REPAIR_CAP, Z3_REPAIR_FINAL_FLOOR)
    progress: dict[str, Any] = {
        "schema_version": "nagv_progress_v3_z3",
        "work_dir": str(work_dir),
        "z3_repair_cap": Z3_REPAIR_CAP,
        "z3_repair_final_floor": Z3_REPAIR_FINAL_FLOOR,
        "z3_repair_used": 0,
        "semantic_rounds_cap": SEMANTIC_ROUNDS,
        "semantic_inner_cap": SEMANTIC_INNER_CAP,
    }
    _save_json(work_dir / "nagv_progress.json", progress)

    if not skip_wfm:
        if nl_file is None:
            return finalize_run(
                NagvRunResult("error_config", "--nl-file required when WFM is not skipped", work_dir)
            )
        rc = run_wfm_until_complete(
            repo_root=repo_root,
            nl_file=nl_file,
            work_dir=work_dir,
            rules_per_chunk=rules_per_chunk,
            reset_progress=reset_wfm_progress,
            print_fn=print_fn,
        )
        if rc != 0:
            return finalize_run(
                NagvRunResult("error_wfm", f"WFM phase exited {rc}", work_dir, detail={"wfm_rc": rc})
            )

    bundle = aggregate_wfm_nl_for_nagv(repo_root=repo_root, work_dir=work_dir, print_fn=print_fn)
    if not bundle.ok:
        detail_bo: dict[str, Any] = {
            "blocking_lines": bundle.blocking_lines,
            "forward_line_count": bundle.forward_line_count,
        }
        return finalize_run(
            NagvRunResult(bundle.outcome, bundle.message, work_dir, detail=detail_bo),
        )
    nl = bundle.nl
    apply_nagv_gemini_post_wfm_thinking()

    out_py = work_dir / "candidate_verified.py"
    code: str | None = None
    aligned = False

    try:
        for sem_round in range(SEMANTIC_ROUNDS):
            print_fn(f"\n--- Semantic outer round {sem_round + 1}/{SEMANTIC_ROUNDS} ---\n")

            code_a, st_a = produce_initial_syntax_ok_code(
                nl=nl,
                candidates_dir=candidates_root / f"sem{sem_round}_syntax",
                tag=f"sem{sem_round}_syntax",
                print_fn=print_fn,
            )
            if st_a == "out_of_scope":
                return finalize_run(
                    NagvRunResult(
                        "rejected_out_of_scope",
                        "Formalizer returned ABORT (encoding not possible without changing NL meaning).",
                        work_dir,
                    )
                )
            if st_a == "unparseable_formalizer":
                return finalize_run(
                    NagvRunResult(
                        "rejected_formalizer_output",
                        "Formalizer reply had no extractable Python "
                        "(truncated response, missing closing ``` on the code fence, or unexpected format). "
                        "Inspect candidates/<semN>_syntax/*_formalizer_raw.txt.",
                        work_dir,
                    )
                )
            if st_a.startswith("error_api"):
                return finalize_run(NagvRunResult("error_api", st_a, work_dir))
            if code_a is None:
                return finalize_run(
                    NagvRunResult(
                        "rejected_syntax_budget",
                        "Exhausted syntax repair before Z3 feasibility gate",
                        work_dir,
                    )
                )
            code = code_a

            t_ix = 0
            while code is not None:
                out_py.write_text(code, encoding="utf-8")
                z = run_z3(out_py, timeout_sec=solver_timeout_sec, phase="feasibility")
                _write_verification_log(work_dir, z)
                _merge_nagv_progress(work_dir, {"z3_repair_used": budget.used})

                if z.kind == "missing":
                    return finalize_run(
                        NagvRunResult(
                            "error_z3_env",
                            "z3-solver not available in NagV venv (pip install z3-solver). "
                            + (z.stderr or z.stdout)[:2000],
                            work_dir,
                        )
                    )
                if z.kind == "timeout":
                    return finalize_run(NagvRunResult("error_timeout", z.stderr, work_dir))
                if z.kind == "tool_failure":
                    detail_tf = {
                        "z3": {"kind": z.kind, "exit_code": z.exit_code},
                        "last_z3_stdout": (z.stdout or "")[:8000],
                        "last_z3_stderr": (z.stderr or "")[:8000],
                    }
                    return finalize_run(
                        NagvRunResult(
                            "error_z3_tool",
                            "Z3 driver failed for a non-candidate reason. See verification_log.txt.",
                            work_dir,
                            detail=detail_tf,
                        )
                    )

                if z3_feasibility_passed(z):
                    break

                if not budget.can_repair_phase_b():
                    return finalize_run(
                        NagvRunResult(
                            "rejected_z3_feasibility_budget",
                            f"Z3 feasibility gate: repair budget exhausted (used {budget.used}/{budget.cap}, "
                            f"floor {budget.floor})",
                            work_dir,
                            detail={
                                "last_z3_stdout": (z.stdout or "")[:4000],
                                "last_z3_stderr": (z.stderr or "")[:4000],
                                "z3_payload": z.payload,
                            },
                        )
                    )

                z_diag = f"Z3 feasibility gate (attempt {t_ix + 1}).\n{format_z3_diagnostic(z)}"
                code2, rst = solver_repair_only_align(
                    nl=nl,
                    repair_bootstrap=(code, z_diag),
                    candidates_dir=candidates_root / f"sem{sem_round}_z3b{t_ix}",
                    tag=f"sem{sem_round}_z3b{t_ix}",
                    budget=budget,
                    phase="b",
                    print_fn=print_fn,
                )
                t_ix += 1
                if rst == "out_of_scope":
                    return finalize_run(NagvRunResult("rejected_out_of_scope", "Repair agent ABORT", work_dir))
                if rst.startswith("error_api"):
                    return finalize_run(NagvRunResult("error_api", rst, work_dir))
                if code2 is None:
                    return finalize_run(
                        NagvRunResult(
                            "rejected_z3_feasibility_budget",
                            f"Feasibility gate repair failed ({rst})",
                            work_dir,
                            detail={
                                "last_z3_stdout": (z.stdout or "")[:4000],
                                "last_z3_stderr": (z.stderr or "")[:4000],
                                "z3_payload": z.payload,
                            },
                        )
                    )
                code = code2

            assert code is not None

            code_s, st_s = semantic_repair_align(
                nl=nl,
                code=code,
                candidates_dir=candidates_root / f"sem{sem_round}_semantic",
                tag=f"sem{sem_round}_semantic",
                print_fn=print_fn,
            )
            if st_s == "out_of_scope":
                return finalize_run(NagvRunResult("rejected_out_of_scope", "Semantic repair ABORT", work_dir))
            if st_s.startswith("error_api"):
                return finalize_run(NagvRunResult("error_api", st_s, work_dir))
            if st_s == "aligned" and code_s is not None:
                code = code_s
                aligned = True
                break
            if sem_round == SEMANTIC_ROUNDS - 1:
                return finalize_run(
                    NagvRunResult(
                        "rejected_semantic_budget",
                        f"Semantic alignment exhausted after {SEMANTIC_ROUNDS} outer round(s) ({st_s})",
                        work_dir,
                    )
                )
            code = None

        if not aligned or code is None:
            return finalize_run(
                NagvRunResult("rejected_semantic_budget", "Semantic alignment incomplete", work_dir)
            )

        budget.mark_semantic_complete()
        _merge_nagv_progress(work_dir, {"semantic_phase_complete": True, "z3_repair_used": budget.used})

        d_ix = 0
        while True:
            out_py.write_text(code, encoding="utf-8")
            z = run_z3(out_py, timeout_sec=solver_timeout_sec, phase="verify")
            _write_verification_log(work_dir, z)
            _merge_nagv_progress(work_dir, {"z3_repair_used": budget.used})

            if z.ok:
                final = work_dir / "final.py"
                shutil.copy2(out_py, final)
                return finalize_run(
                    NagvRunResult(
                        "success",
                        "Z3 check succeeded (expected sat)",
                        work_dir,
                        final_py=final,
                        detail={
                            "z3": {
                                "kind": z.kind,
                                "status": z.z3_status,
                                "unsat_core": z.unsat_core,
                            }
                        },
                    )
                )

            if z.kind == "missing":
                return finalize_run(NagvRunResult("error_z3_env", z.stderr, work_dir))
            if z.kind == "timeout":
                return finalize_run(NagvRunResult("error_timeout", z.stderr, work_dir))
            if z.kind == "tool_failure":
                detail_tf2 = {
                    "z3": {"kind": z.kind, "exit_code": z.exit_code},
                    "last_z3_stdout": (z.stdout or "")[:8000],
                    "last_z3_stderr": (z.stderr or "")[:8000],
                }
                return finalize_run(
                    NagvRunResult(
                        "error_z3_tool",
                        "Z3 driver tool failure during final verify. See verification_log.txt.",
                        work_dir,
                        detail=detail_tf2,
                    )
                )

            if not budget.can_repair_phase_d():
                return finalize_run(
                    NagvRunResult(
                        "rejected_z3_verify_budget",
                        f"Final Z3 verify: repair budget exhausted (used {budget.used}/{budget.cap})",
                        work_dir,
                        detail={
                            "last_z3_stdout": (z.stdout or "")[:4000],
                            "last_z3_stderr": (z.stderr or "")[:4000],
                            "z3_payload": z.payload,
                        },
                    )
                )

            z_diag = f"Z3 final verify — {z.kind} (attempt {d_ix + 1}).\n{format_z3_diagnostic(z)}"
            code2, rst = solver_repair_only_align(
                nl=nl,
                repair_bootstrap=(code, z_diag),
                candidates_dir=candidates_root / f"phase_d_{d_ix}",
                tag=f"phase_d_{d_ix}",
                budget=budget,
                phase="d",
                print_fn=print_fn,
            )
            d_ix += 1
            if rst == "out_of_scope":
                return finalize_run(NagvRunResult("rejected_out_of_scope", "Repair agent ABORT", work_dir))
            if rst.startswith("error_api"):
                return finalize_run(NagvRunResult("error_api", rst, work_dir))
            if code2 is None:
                return finalize_run(
                    NagvRunResult(
                        "rejected_z3_verify_budget",
                        f"Final verify repair failed ({rst})",
                        work_dir,
                        detail={
                            "last_z3_stdout": (z.stdout or "")[:4000],
                            "last_z3_stderr": (z.stderr or "")[:4000],
                            "z3_payload": z.payload,
                        },
                    )
                )
            code = code2

    except Exception as e:
        traceback.print_exc()
        return finalize_run(NagvRunResult("error_api", str(e), work_dir))

    return finalize_run(NagvRunResult("error_config", "Internal: run_nagv fell through", work_dir))
