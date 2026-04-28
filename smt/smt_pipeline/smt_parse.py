"""Parse SMT-LIB with Z3 (in-process), bounded timeout."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Tuple


def parse_smt2_string_check(s: str, *, timeout_sec: float) -> Tuple[bool, str]:
    """
    Returns (ok, error_message). On success error_message is empty.
    Uses Z3's SMT-LIB parser — policy artifact is SMT-LIB, not Python.
    """

    def _parse() -> None:
        import z3

        z3.parse_smt2_string(s)

    if not s.strip():
        return False, "empty_smt2_string"

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_parse)
            fut.result(timeout=timeout_sec)
        return True, ""
    except FuturesTimeout:
        return False, f"parse_timeout_after_{timeout_sec}s"
    except Exception as e:
        return False, str(e)
