"""LLM agent: policy context → validated TemplateSuiteFile (executable tests)."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.llm import pivot_llm_complete
from pivot_pipeline.paths import PROMPTS_DIR
from pivot_pipeline.template_generator_context import build_template_generator_context
from pivot_pipeline.template_suite.schemas import TemplateSuiteFile


def _max_rounds() -> int:
    raw = os.getenv("PIVOT_TEMPLATE_GEN_MAX_ROUNDS", "3").strip()
    try:
        n = int(raw)
        return max(1, min(n, 8))
    except ValueError:
        return 3


def _load_prompt() -> str:
    p = PROMPTS_DIR / "template_generator.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing prompt {p}")
    return p.read_text(encoding="utf-8")


def run_template_generator(
    *,
    work_dir: Path,
    llm_complete: Callable[..., str] | None = None,
    max_rounds: int | None = None,
) -> tuple[TemplateSuiteFile, str]:
    """
    Call LLM with policy context; parse JSON; validate TemplateSuiteFile.
    Returns (suite, last_raw_model_text).
    """
    work_dir = work_dir.resolve()
    llm = llm_complete or pivot_llm_complete
    system_and_template = _load_prompt()
    context = build_template_generator_context(work_dir)
    mr = max_rounds if max_rounds is not None else _max_rounds()

    feedback = ""
    last_raw = ""
    for attempt in range(mr):
        user = (
            f"{context}\n\n"
            "Generate the template suite JSON object as specified in your instructions.\n"
        )
        if feedback:
            user += f"\nPrevious attempt failed validation:\n{feedback}\nFix and output valid JSON only.\n"

        prompt = f"{system_and_template}\n\n---\n\nUSER:\n{user}"
        last_raw = llm(prompt)
        (work_dir / "template_generator_raw.txt").write_text(last_raw, encoding="utf-8")
        try:
            obj = parse_json_object(last_raw)
            suite = TemplateSuiteFile.model_validate(obj)
            return suite, last_raw
        except (ValueError, ValidationError) as e:
            feedback = f"{type(e).__name__}: {e}"
            if attempt == mr - 1:
                raise
    raise RuntimeError("template generator: exhausted retries")


def run_template_generator_pipeline(
    *,
    work_dir: Path,
    llm_complete: Callable[..., str] | None = None,
    max_rounds: int | None = None,
) -> Path:
    """Generate suite, write ``template_suite_generated.json``; return path."""
    work_dir = work_dir.resolve()
    suite, _raw = run_template_generator(work_dir=work_dir, llm_complete=llm_complete, max_rounds=max_rounds)
    out = work_dir / "template_suite_generated.json"
    out.write_text(suite.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return out


__all__ = [
    "run_template_generator",
    "run_template_generator_pipeline",
]
