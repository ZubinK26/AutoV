"""Formalizer prompt file selection (revert path: unset env → v3)."""

from __future__ import annotations

import os

from smt_pipeline.llm_steps import load_formalizer_prompt_name


def test_default_formalizer_prompt_is_v3(monkeypatch) -> None:
    monkeypatch.delenv("SMT_PIPELINE_FORMALIZER_PROMPT", raising=False)
    assert load_formalizer_prompt_name() == "formalizer_v3.md"


def test_env_overrides_formalizer_prompt(monkeypatch) -> None:
    monkeypatch.setenv("SMT_PIPELINE_FORMALIZER_PROMPT", "formalizer_v3_with_preformalization.md")
    assert load_formalizer_prompt_name() == "formalizer_v3_with_preformalization.md"
