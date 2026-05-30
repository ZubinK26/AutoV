"""Flash syntax repair for fill JSON after review PASS."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from pivot_pipeline.external_tester.api_retry import call_with_api_retries
from pivot_pipeline.external_tester.llm import external_llm_complete
from pivot_pipeline.external_tester.schemas import ExternalWorldFillV1
from pivot_pipeline.external_tester.trace import append_trace
from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.paths import PROMPTS_DIR


def _syntax_max() -> int:
    raw = os.getenv("PIVOT_EXTERNAL_SYNTAX_REPAIR_MAX", "3").strip()
    try:
        return max(1, min(int(raw), 8))
    except ValueError:
        return 3


def _trim(s: str, n: int = 6000) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 20] + "\n... (truncated)\n"


def repair_fill_json(
    *,
    work_dir: Path,
    invalid_raw: str,
    error: str,
) -> ExternalWorldFillV1:
    system = (PROMPTS_DIR / "external_world_syntax_repair.md").read_text(encoding="utf-8")
    mr = _syntax_max()
    feedback = error
    last_raw = invalid_raw

    for attempt in range(mr):
        user = (
            f"{system}\n\n---\n\n"
            f"Validation error:\n{feedback}\n\n"
            f"Invalid JSON:\n{_trim(last_raw)}\n\n"
            "Output corrected ExternalWorldFillV1 JSON only."
        )
        last_raw = call_with_api_retries(
            lambda: external_llm_complete(user, stage="syntax"),
            label="external_syntax",
        )
        append_trace(work_dir, {"kind": "syntax_repair", "attempt": attempt + 1})
        try:
            obj = parse_json_object(last_raw)
            return ExternalWorldFillV1.model_validate(obj)
        except (ValueError, ValidationError) as e:
            feedback = f"{type(e).__name__}: {e}"
            continue

    raise RuntimeError(f"external syntax repair failed after {mr} attempts: {feedback}")


__all__ = ["repair_fill_json"]
