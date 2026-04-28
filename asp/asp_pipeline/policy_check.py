"""
Clingo satisfiability / answer-set check for a committed ``.lp`` (``docs/pipeline_wfm_to_asp.md`` §8).

Run: ``python -m asp_pipeline.policy_check <file.lp>``

Programs with ClinCon ``&sum{...}`` are solved via **clingcon** (Python API); plain ``clingo`` on PATH
does not load the constraint theory.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from asp_pipeline.clingo_check import _resolve_clingo_exe
from asp_pipeline.clingcon_api import (
    program_uses_clincon_sum,
    solve_clincon,
    use_clincon_grounding_enabled,
)


def _run_policy_check_embedded(policy_lp: Path) -> dict[str, Any]:
    try:
        from clingo import Control
    except ImportError:
        return {
            "status": "ERROR",
            "answer_set_count": None,
            "unsat_core": None,
            "detail": "clingo executable not found; install Python package: pip install clingo",
        }
    text = policy_lp.read_text(encoding="utf-8")
    try:
        c = Control()
        c.add("base", [], text)
        c.ground([("base", [])])
    except Exception as e:  # noqa: BLE001
        return {
            "status": "ERROR",
            "answer_set_count": None,
            "unsat_core": None,
            "detail": str(e)[:4000],
        }
    h = c.solve()
    if h.unsatisfiable:
        return {
            "status": "UNSATISFIABLE",
            "answer_set_count": 0,
            "unsat_core": None,
        }
    if h.satisfiable:
        return {
            "status": "SATISFIABLE",
            "answer_set_count": 1,
            "unsat_core": None,
        }
    return {
        "status": "ERROR",
        "answer_set_count": None,
        "unsat_core": None,
        "detail": "solve result neither satisfiable nor unsatisfiable",
    }


def run_policy_check(
    policy_lp: Path,
    *,
    max_models: int = 1,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    if not policy_lp.is_file():
        return {"status": "ERROR", "answer_set_count": None, "unsat_core": None, "detail": f"file not found: {policy_lp}"}
    text = policy_lp.read_text(encoding="utf-8")

    if program_uses_clincon_sum(text):
        if not use_clincon_grounding_enabled():
            return {
                "status": "ERROR",
                "answer_set_count": None,
                "unsat_core": None,
                "detail": "policy uses &sum{...}; set ASP_PIPELINE_USE_CLINGCON=1 (default) and pip install clingcon",
            }
        st, n, det = solve_clincon(text, max_models=max_models, timeout_sec=timeout_sec)
        if st == "SATISFIABLE":
            return {"status": "SATISFIABLE", "answer_set_count": n, "unsat_core": None}
        if st == "UNSATISFIABLE":
            return {"status": "UNSATISFIABLE", "answer_set_count": 0, "unsat_core": None}
        return {
            "status": "ERROR",
            "answer_set_count": None,
            "unsat_core": None,
            "detail": det or "clingcon solve error",
        }

    exe = _resolve_clingo_exe()
    if not exe:
        return _run_policy_check_embedded(policy_lp)
    try:
        proc = subprocess.run(
            [exe, str(policy_lp), "-n", str(max_models), "--outf=1"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "ERROR",
            "answer_set_count": None,
            "unsat_core": None,
            "detail": f"clingo timed out after {timeout_sec}s",
        }
    out = (proc.stdout or "") + (proc.stderr or "")
    u = out.upper()
    if "UNSATISFIABLE" in u or proc.returncode == 20 or ("UNSAT" in u and "UNSATISFIABLE" in u):
        return {
            "status": "UNSATISFIABLE",
            "answer_set_count": 0,
            "unsat_core": None,
            "clingo_return_code": proc.returncode,
        }
    if "SATISFIABLE" in u or (proc.returncode in (0, 1, 10) and "Answer:" in out):
        m = re.findall(r"^Answer:\s*(\d+)", out, re.MULTILINE)
        n = len(m) or 1
        return {
            "status": "SATISFIABLE",
            "answer_set_count": n,
            "unsat_core": None,
            "clingo_return_code": proc.returncode,
        }
    if proc.returncode in (0, 10) and "Answer" in out:
        return {
            "status": "SATISFIABLE",
            "answer_set_count": 1,
            "unsat_core": None,
            "clingo_return_code": proc.returncode,
        }
    if proc.returncode == 20:
        return {"status": "UNSATISFIABLE", "answer_set_count": 0, "unsat_core": None, "clingo_return_code": 20}
    return {
        "status": "ERROR",
        "answer_set_count": None,
        "unsat_core": None,
        "detail": out[:4000] or f"clingo exit {proc.returncode}",
        "clingo_return_code": proc.returncode,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Clingo check: satisfiability of a .lp file.")
    p.add_argument("file", type=Path, help="Clingo/ClinCon program (.lp).")
    p.add_argument("--max-models", type=int, default=1)
    p.add_argument("--timeout-sec", type=float, default=60.0)
    a = p.parse_args(argv)
    r = run_policy_check(a.file, max_models=a.max_models, timeout_sec=a.timeout_sec)
    print(json.dumps(r, indent=2, ensure_ascii=False))
    if r.get("status") == "SATISFIABLE":
        return 0
    if r.get("status") == "UNSATISFIABLE":
        return 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
