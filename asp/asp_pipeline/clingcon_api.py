"""Potassco **clingcon** integration for ClinCon `&sum{{...}}` (see ``docs/pipeline_wfm_to_asp.md`` §2.1).

Plain ``Control().add(...); .ground()`` cannot define theory atom ``sum/0``; programs using ``&sum`` must
be loaded via ``parse_string`` + ``ProgramBuilder`` and ``Theory('clingcon', ...).rewrite_ast`` (Potassco).
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

# Constraint theory atoms in scope for the ClinCon product line (extend when spec §2.1 does).
RE_CLINCON_SUM = re.compile(r"&\s*sum\s*\{")


def program_uses_clincon_sum(lp: str) -> bool:
    """True if the program text may require clingcon (linear ``&sum{{...}}`` constraints)."""
    return bool(RE_CLINCON_SUM.search(lp or ""))


def use_clincon_grounding_enabled() -> bool:
    """Default on; set ``ASP_PIPELINE_USE_CLINGCON=0`` to fall back to plain Clingo only (theory will fail)."""
    v = (os.environ.get("ASP_PIPELINE_USE_CLINGCON") or "1").strip().lower()
    return v not in ("0", "false", "no")


def _clingcon_lib() -> tuple[Any, Any] | None:
    try:
        from clingcon._clingcon import lib, ffi  # type: ignore[import-not-found]
    except ImportError:
        return None
    return (lib, ffi)


def clingcon_import_error_message() -> str | None:
    if _clingcon_lib() is None:
        return (
            "The program uses ClinCon &sum{...} constraints; the 'clingcon' package is required. "
            "Install: pip install clingcon  (see docs/pipeline_wfm_to_asp.md, Tooling / oracle)"
        )
    return None


def _control_with_clincon_program(prg: str) -> tuple[Any, Any]:
    """Parse ``prg`` into a new ``Control`` with clingcon; returns ``(ctl, thy)`` for ``prepare`` / ``on_model``."""
    from clingo import Control
    from clingo.ast import parse_string, ProgramBuilder
    from clingo.theory import Theory

    lib, ffi = _clingcon_lib()  # type: ignore[union-attr]
    thy = Theory("clingcon", lib, ffi)
    ctl = Control(["0"])
    thy.register(ctl)
    with ProgramBuilder(ctl) as bld:
        parse_string(prg, lambda ast: thy.rewrite_ast(ast, bld.add))
    return ctl, thy


def parse_only_clincon(
    proposed_lp: str,
    *,
    timeout_sec: float,
) -> tuple[bool, str]:
    """Parse-check ``proposed_lp`` using clingcon's AST rewrite (required for valid ``&sum`` syntax)."""
    cie = clingcon_import_error_message()
    if cie:
        return False, cie

    def go() -> tuple[bool, str]:
        try:
            _control_with_clincon_program(proposed_lp)
        except Exception as e:  # noqa: BLE001
            return False, str(e)[:8000]
        return True, ""

    if timeout_sec <= 0 or timeout_sec >= 1e6:
        return go()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(go)
        try:
            return fut.result(timeout=timeout_sec)
        except FutureTimeout:
            return False, "clingcon: parse timed out"


def ground_clincon(
    combined_lp: str,
    *,
    timeout_sec: float,
) -> tuple[bool, str]:
    """Ground ``combined_lp`` (existing policy + proposed chunk) with clingcon registered."""
    cie = clingcon_import_error_message()
    if cie:
        return False, cie

    def go() -> tuple[bool, str]:
        try:
            ctl, _ = _control_with_clincon_program(combined_lp)
            ctl.ground([("base", [])])
        except Exception as e:  # noqa: BLE001
            u = str(e).lower()
            if "unsafe" in u:
                return False, str(e)[:8000]
            return False, str(e)[:8000]
        return True, ""

    if timeout_sec <= 0 or timeout_sec >= 1e6:
        return go()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(go)
        try:
            return fut.result(timeout=timeout_sec)
        except FutureTimeout:
            return False, "clingcon: ground timed out"


def solve_clincon(
    full_lp: str,
    *,
    max_models: int = 1,
    timeout_sec: float = 60.0,
) -> tuple[str, int | None, str | None]:
    """
    Returns (status, answer_set_count_or_none, detail_or_none)
    where status is ``SATISFIABLE``, ``UNSATISFIABLE``, or ``ERROR``.
    """
    cie = clingcon_import_error_message()
    if cie:
        return "ERROR", None, cie

    def go() -> tuple[str, int | None, str | None]:
        try:
            ctl, thy = _control_with_clincon_program(full_lp)
            ctl.ground([("base", [])])
            thy.prepare(ctl)
        except Exception as e:  # noqa: BLE001
            return "ERROR", None, str(e)[:4000]

        n_found = 0

        def on_m(model: Any) -> bool | None:
            nonlocal n_found
            thy.on_model(model)
            n_found += 1
            return n_found < max_models

        try:
            h = ctl.solve(on_model=on_m)
        except Exception as e:  # noqa: BLE001
            return "ERROR", None, str(e)[:4000]
        r = h
        if r.unsatisfiable:
            return "UNSATISFIABLE", 0, None
        if r.satisfiable:
            return "SATISFIABLE", n_found if n_found > 0 else 1, None
        return "ERROR", None, "solve: unknown satisfiability result"

    if timeout_sec <= 0 or timeout_sec >= 1e6:
        return go()
    with ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(go)
        try:
            return fut.result(timeout=timeout_sec)
        except FutureTimeout:
            return "ERROR", None, f"clingcon: solve timed out after {timeout_sec}s"
