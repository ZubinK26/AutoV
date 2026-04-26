"""Clingo `parse-only` and `ground` checks (`docs/pipeline_wfm_to_asp.md` §4)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple


def clingo_path() -> str | None:
    return os.environ.get("CLINGO_PATH") or shutil.which("clingo")


def _repo_local_clingo_exe() -> Path | None:
    """Optional bundled Windows binary: ``<repo>/tools/clingo/clingo.exe``."""
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        cand = parent / "tools" / "clingo" / "clingo.exe"
        if cand.is_file():
            return cand
    return None


def _resolve_clingo_exe() -> str | None:
    p = clingo_path()
    if p:
        return p
    loc = _repo_local_clingo_exe()
    if loc is not None:
        return str(loc)
    return None


def _parse_only_embedded(proposed_lp: str) -> tuple[bool, str]:
    try:
        from clingo import Control
    except ImportError:
        return (
            False,
            "clingo: no 'clingo' on PATH and Python package 'clingo' is not installed "
            "(pip install clingo, or set CLINGO_PATH, or place clingo.exe under tools/clingo/)",
        )
    try:
        ctl = Control()
        ctl.add("base", [], proposed_lp)
    except Exception as e:  # noqa: BLE001 — surface parse errors
        return False, str(e)[:8000]
    return True, ""


def _ground_embedded(existing_policy: str, proposed_lp: str) -> tuple[bool, str]:
    try:
        from clingo import Control
    except ImportError:
        return (
            False,
            "clingo: no 'clingo' on PATH and Python package 'clingo' is not installed",
        )
    combined = _combined_text(existing_policy, proposed_lp)
    try:
        ctl = Control()
        ctl.add("base", [], combined)
        ctl.ground([("base", [])])
    except Exception as e:  # noqa: BLE001
        u = str(e).lower()
        if "unsafe" in u:
            return False, str(e)[:8000]
        return False, str(e)[:8000]
    return True, ""


def _write_temp_lp(content: str) -> Path:
    fd, name = tempfile.mkstemp(suffix=".lp", text=True)
    os.close(fd)
    p = Path(name)
    p.write_text(content, encoding="utf-8")
    return p


def _run_clingo(
    args: list[str],
    inp: Path,
    *,
    timeout_sec: float,
) -> tuple[int, str, str]:
    exe = _resolve_clingo_exe()
    if not exe:
        return (127, "", "clingo: executable not found (install Clingo and/or set CLINGO_PATH)")

    try:
        proc = subprocess.run(
            [exe, *args, str(inp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return (124, "", "clingo subprocess timed out")
    out = (proc.stdout or "") + (proc.stderr or "")
    return (proc.returncode, out, (proc.stderr or ""))


def check_parse_only(
    proposed_lp: str,
    *,
    timeout_sec: float,
) -> tuple[bool, str]:
    """
    Run ``clingo --parse-only`` on a temp file. Pass if exit 0 and stderr does not look like a hard error.
    If the ``clingo`` executable is missing, fall back to the **Python** ``clingo`` package (``pip install clingo``),
    which provides the same parse check via the C API.
    """
    p = _write_temp_lp(proposed_lp)
    try:
        code, _, err = _run_clingo(
            ["--parse-only"],
            p,
            timeout_sec=timeout_sec,
        )
        if code != 127:
            if code == 124:
                return False, "parse-only timed out"
            err_l = (err or "").lower()
            if code != 0:
                return False, (err or "parse failed")[:8000]
            if "error:" in err_l or "syntax" in err_l and "error" in err_l:
                return False, (err or "")[:8000]
            return True, ""
    finally:
        p.unlink(missing_ok=True)

    return _parse_only_embedded(proposed_lp)


def _combined_text(existing: str, proposed: str) -> str:
    e = (existing or "").strip()
    pr = (proposed or "").strip()
    if not e:
        return pr
    if not pr:
        return e
    return e + "\n\n" + pr


def check_ground(
    existing_policy: str,
    proposed_lp: str,
    *,
    timeout_sec: float,
) -> tuple[bool, str]:
    """
    Concatenate existing + proposed, then ``clingo --ground --output=text`` per spec.
    If the ``clingo`` executable is missing, fall back to grounding via the **Python** ``clingo`` package.
    """
    p = _write_temp_lp(_combined_text(existing_policy, proposed_lp))
    try:
        code, combined, err = _run_clingo(
            ["--ground", "--output=text", "--outf=0"],
            p,
            timeout_sec=timeout_sec,
        )
        if code != 127:
            uerr = (err + "\n" + combined).lower()
            if "unsafe variable" in uerr:
                return False, (err.strip() or combined)[:8000]
            if code == 0:
                if not err.strip():
                    return True, ""
                if "warning" in err.lower() and "error" not in err.lower():
                    return True, ""
            if code == 124:
                return False, "grounding timed out"
            detail = (err.strip() or combined)[:8000] or f"clingo --ground exit {code}"
            return False, detail
    finally:
        p.unlink(missing_ok=True)

    return _ground_embedded(existing_policy, proposed_lp)


def check_parse_and_ground(
    existing_policy: str,
    proposed_lp: str,
    *,
    parse_timeout_sec: float,
    ground_timeout_sec: float,
) -> tuple[bool, str, str]:
    """
    Returns (ok, stage, error) where stage is ``parse`` or ``grounding`` on failure.
    """
    okp, e1 = check_parse_only(proposed_lp, timeout_sec=parse_timeout_sec)
    if not okp:
        return False, "parse", e1
    okg, e2 = check_ground(existing_policy, proposed_lp, timeout_sec=ground_timeout_sec)
    if not okg:
        if "unsafe variable" in (e2 or "").lower():
            return False, "grounding", e2
        if "timeout" in (e2 or "").lower() or "timed out" in (e2 or "").lower():
            return False, "grounding", e2
        return False, "grounding", e2
    return True, "", ""


# strip accidental ``` fences from model output
_FENCE = re.compile(r"^\s*```(?:lp|asp|prolog|text)?\s*", re.IGNORECASE | re.MULTILINE)
_FENCE_END = re.compile(r"```\s*$", re.MULTILINE)


def strip_lp_fences(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z0-9]*\s*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    return t.strip()
