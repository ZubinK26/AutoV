"""Blind provenance reviewer agent."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from pivot_pipeline.external_tester.api_retry import call_with_api_retries
from pivot_pipeline.external_tester.llm import external_llm_complete
from pivot_pipeline.external_tester.review_aggregate import aggregate_review
from pivot_pipeline.external_tester.review_pack import build_blind_review_user_message
from pivot_pipeline.external_tester.schemas import (
    ExternalProvenanceReviewV1,
    ExternalSourceEnvelope,
    ExternalWorldFillV1,
    FieldProvenanceReview,
)
from pivot_pipeline.external_tester.trace import append_trace
from pivot_pipeline.ir import MetaScheme
from pivot_pipeline.json_util import parse_json_object
from pivot_pipeline.paths import PROMPTS_DIR


def _review_max_rounds() -> int:
    raw = os.getenv("PIVOT_EXTERNAL_REVIEW_MAX_ROUNDS", "3").strip()
    try:
        return max(1, min(int(raw), 8))
    except ValueError:
        return 3


def _load_review_prompt() -> str:
    return (PROMPTS_DIR / "external_world_provenance_review.md").read_text(encoding="utf-8")


def run_review_agent(
    *,
    work_dir: Path,
    source: ExternalSourceEnvelope,
    fill: ExternalWorldFillV1,
    meta: MetaScheme,
) -> ExternalProvenanceReviewV1:
    hints = {n: f"sort={meta.variable_sorts[n]}" for n in sorted(meta.variable_sorts.keys())}
    user_body = build_blind_review_user_message(source, fill, catalog_one_liners=hints)
    prompt = f"{_load_review_prompt()}\n\n---\n\nUSER:\n{user_body}"
    mr = _review_max_rounds()
    last_raw = ""
    feedback = ""

    for attempt in range(mr):
        p = prompt if not feedback else f"{prompt}\n\nPrevious parse error:\n{feedback}\n"
        last_raw = call_with_api_retries(
            lambda: external_llm_complete(p, stage="review"),
            label="external_review",
        )
        (work_dir / "external_provenance_review_raw.txt").write_text(last_raw, encoding="utf-8")
        append_trace(work_dir, {"kind": "review", "attempt": attempt + 1})
        try:
            obj = parse_json_object(last_raw)
            partial = obj.get("field_reviews")
            if not isinstance(partial, list):
                raise ValueError("field_reviews must be a list")
            reviews = [FieldProvenanceReview.model_validate(x) for x in partial]
            out = aggregate_review(fill, reviews)
            (work_dir / "external_provenance_review.json").write_text(
                json.dumps(out.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return out
        except (ValueError, ValidationError) as e:
            feedback = f"{type(e).__name__}: {e}"
            continue

    raise RuntimeError(f"external review exhausted {mr} rounds: {feedback}; raw len={len(last_raw)}")


__all__ = ["run_review_agent"]
