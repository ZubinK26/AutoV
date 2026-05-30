"""Compact rule glossary for phase-2 derive (no document re-read)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pivot_pipeline.assessment_linearize import build_assessment_linearized


def build_rule_glossary(
    rules: list[dict[str, Any]],
    *,
    work_dir: Path | None = None,
    max_chars: int | None = None,
) -> str:
    """Prefer existing linearized artifact; else build from rules JSON."""
    cap = max_chars
    if cap is None:
        raw = os.getenv("PIVOT_EXTERNAL_RULE_GLOSSARY_MAX_CHARS", "8000").strip()
        try:
            cap = int(raw)
        except ValueError:
            cap = 8000

    if work_dir is not None:
        for name in (
            "linearized_model_for_assessment.txt",
            "linearized_model_for_cross_critic.txt",
        ):
            p = work_dir / name
            if p.is_file():
                text = p.read_text(encoding="utf-8")
                if len(text) <= cap:
                    return text
                return text[: cap - 40] + "\n... (truncated)\n"

    text = build_assessment_linearized(rules)
    if len(text) <= cap:
        return text
    return text[: cap - 40] + "\n... (truncated)\n"


__all__ = ["build_rule_glossary"]
