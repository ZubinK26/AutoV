"""Run formalizer candidate via ``z3_driver`` subprocess; classify for pipeline phases."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Z3Result:
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    kind: str  # success | feasibility | feasibility_pass | verification | tool_failure | timeout | missing
    feasibility_ok: bool
    z3_status: str | None
    unsat_core: list[str] | None
    payload: dict[str, Any] | None
    phase: str


def _nagv_dir_for_subprocess() -> Path:
    return Path(__file__).resolve().parent.parent


def _parse_driver_json(stdout: str) -> dict[str, Any] | None:
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


def run_z3(py_file: Path, *, timeout_sec: int = 120, phase: str = "verify") -> Z3Result:
    """
    Execute candidate in isolated process.

    ``phase`` is ``feasibility`` or ``verify`` (passed to driver for logging; same check today).
    """
    nagv_dir = _nagv_dir_for_subprocess()
    env = os.environ.copy()
    prefix = str(nagv_dir)
    old = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = f"{prefix}{os.pathsep}{old}" if old else prefix

    cmd = [
        sys.executable,
        "-m",
        "nagv.z3_driver",
        str(py_file.resolve()),
        phase,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=str(nagv_dir),
            env=env,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        return Z3Result(
            ok=False,
            exit_code=-124,
            stdout="",
            stderr=f"Z3 driver timed out after {timeout_sec}s",
            kind="timeout",
            feasibility_ok=False,
            z3_status=None,
            unsat_core=None,
            payload=None,
            phase=phase,
        )

    out = proc.stdout or ""
    err = proc.stderr or ""
    payload = _parse_driver_json(out)

    if payload is None:
        combined = (out + "\n" + err).lower()
        if "no module named 'z3'" in combined or (
            "importerror" in combined and "z3" in combined
        ):
            return Z3Result(
                ok=False,
                exit_code=proc.returncode,
                stdout=out,
                stderr=err,
                kind="missing",
                feasibility_ok=False,
                z3_status=None,
                unsat_core=None,
                payload=None,
                phase=phase,
            )
        return Z3Result(
            ok=False,
            exit_code=proc.returncode,
            stdout=out,
            stderr=err,
            kind="tool_failure",
            feasibility_ok=False,
            z3_status=None,
            unsat_core=None,
            payload=None,
            phase=phase,
        )

    fe_ok = bool(payload.get("ok_feasibility"))
    status = payload.get("status")
    if status is not None:
        status = str(status).lower()
    uc = payload.get("unsat_core")
    core_list: list[str] | None = None
    if isinstance(uc, list):
        core_list = [str(x) for x in uc]

    if not fe_ok:
        return Z3Result(
            ok=False,
            exit_code=proc.returncode,
            stdout=out,
            stderr=err,
            kind="feasibility",
            feasibility_ok=False,
            z3_status=status,
            unsat_core=core_list,
            payload=payload,
            phase=phase,
        )

    if phase == "verify":
        verify_ok = status == "sat"
        if verify_ok:
            return Z3Result(
                ok=True,
                exit_code=0,
                stdout=out,
                stderr=err,
                kind="success",
                feasibility_ok=True,
                z3_status=status,
                unsat_core=core_list,
                payload=payload,
                phase=phase,
            )
        return Z3Result(
            ok=False,
            exit_code=proc.returncode,
            stdout=out,
            stderr=err,
            kind="verification",
            feasibility_ok=True,
            z3_status=status,
            unsat_core=core_list,
            payload=payload,
            phase=phase,
        )

    # feasibility phase: got a Z3 status from run_z3_check
    gk = "feasibility_pass" if status in ("sat", "unsat", "unknown") else "feasibility"
    return Z3Result(
        ok=False,
        exit_code=0,
        stdout=out,
        stderr=err,
        kind=gk,
        feasibility_ok=True,
        z3_status=status,
        unsat_core=core_list,
        payload=payload,
        phase=phase,
    )


def z3_feasibility_passed(z: Z3Result) -> bool:
    """True once candidate runs ``run_z3_check`` and returns a Z3 ``status`` (sat/unsat/unknown)."""
    if not z.feasibility_ok or z.z3_status not in ("sat", "unsat", "unknown"):
        return False
    return True


def format_z3_diagnostic(z: Z3Result) -> str:
    """Human-readable block for repair agent."""
    lines = []
    lines.append(f"phase={z.phase} kind={z.kind} exit={z.exit_code}")
    if z.payload:
        lines.append(f"payload: {json.dumps(z.payload, ensure_ascii=False)[:8000]}")
    lines.append(f"--- stdout ---\n{z.stdout}")
    lines.append(f"--- stderr ---\n{z.stderr}")
    return "\n".join(lines)
