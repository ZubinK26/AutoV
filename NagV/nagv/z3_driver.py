"""Subprocess entry: load formalizer candidate and run ``run_z3_check()`` → JSON on stdout."""

from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path


def _emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def main() -> int:
    if len(sys.argv) < 3:
        _emit({"ok_feasibility": False, "error": "usage: python -m nagv.z3_driver <candidate.py> <feasibility|verify>"})
        return 2
    cand_path = Path(sys.argv[1]).resolve()
    phase = sys.argv[2].strip().lower()
    if phase not in ("feasibility", "verify"):
        _emit({"ok_feasibility": False, "error": f"invalid phase {phase!r}"})
        return 2
    if not cand_path.is_file():
        _emit({"ok_feasibility": False, "error": f"not a file: {cand_path}"})
        return 3
    try:
        spec = importlib.util.spec_from_file_location("_nagv_z3_candidate", cand_path)
        if spec is None or spec.loader is None:
            _emit({"ok_feasibility": False, "error": "spec_from_file_location failed"})
            return 4
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception:
        _emit(
            {
                "ok_feasibility": False,
                "error": "exec_module failed",
                "traceback": traceback.format_exc(),
            }
        )
        return 5

    fn = getattr(mod, "run_z3_check", None)
    if fn is None:
        fn = getattr(mod, "check", None)
    if fn is None:
        _emit({"ok_feasibility": False, "error": "candidate must define run_z3_check() or check()"})
        return 6

    try:
        raw = fn()
    except Exception:
        _emit(
            {
                "ok_feasibility": False,
                "error": "run_z3_check raised",
                "traceback": traceback.format_exc(),
            }
        )
        return 7

    if raw is None:
        _emit({"ok_feasibility": False, "error": "run_z3_check returned None"})
        return 8

    if hasattr(raw, "as_dict"):
        raw = raw.as_dict()
    if not isinstance(raw, dict):
        _emit({"ok_feasibility": False, "error": "run_z3_check must return dict or Z3CheckResult"})
        return 8

    status = raw.get("status")
    if status is not None:
        status = str(status).lower()
        if status not in ("sat", "unsat", "unknown"):
            _emit(
                {
                    "ok_feasibility": False,
                    "error": f"invalid status {raw.get('status')!r}, want sat|unsat|unknown",
                }
            )
            return 9

    ok_f = status is not None
    unsat_core = raw.get("unsat_core")
    if unsat_core is not None and not isinstance(unsat_core, list):
        unsat_core = [str(unsat_core)]
    out = {
        "ok_feasibility": ok_f,
        "status": status,
        "unsat_core": unsat_core,
        "model_excerpt": raw.get("model_excerpt"),
        "diagnostics": raw.get("diagnostics"),
        "phase": phase,
    }
    _emit(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
