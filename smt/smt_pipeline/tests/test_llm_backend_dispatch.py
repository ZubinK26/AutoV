"""SMT formalizer/critic LLM backend dispatch (no API calls)."""

from __future__ import annotations

import pytest

from smt_pipeline.config import SmtPipelineConfig
from smt_pipeline.llm_steps import (
    _critic_llm_backend,
    _formalizer_llm_backend,
    formalizer_smt2_block,
)
from smt_pipeline.models import FormalizerContext


def test_formalizer_dispatches_to_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMT_PIPELINE_SMT_LLM", "anthropic")
    assert _formalizer_llm_backend() == "anthropic"
    monkeypatch.delenv("SMT_PIPELINE_SMT_LLM", raising=False)
    monkeypatch.setenv("SMT_PIPELINE_FORMALIZER_LLM", "gemini")
    monkeypatch.delenv("SMT_PIPELINE_SMT_LLM", raising=False)
    assert _formalizer_llm_backend() == "gemini"


def test_critic_per_agent_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMT_PIPELINE_SMT_LLM", "gemini")
    monkeypatch.setenv("SMT_PIPELINE_CRITIC_LLM", "anthropic")
    assert _critic_llm_backend() == "anthropic"


def test_formalizer_anthropic_invokes_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMT_PIPELINE_FORMALIZER_LLM", "anthropic")
    called: dict[str, str] = {}

    def fake(*, system_instruction: str, user_text: str, max_output_tokens: object = None) -> str:
        called["system"] = system_instruction[:80]
        called["user"] = user_text[:40]
        return "(set-logic ALL)\n(assert true)"

    monkeypatch.setattr("smt_pipeline.anthropic_call.anthropic_complete", fake)
    ctx = FormalizerContext(
        bundle_id="b",
        policy_path="p",
        policy_text="",
        existing_rule_count=0,
        in_scope_lines=['rule_id=r1 line_index=0 statement_nl="x"'],
        attempt_index=0,
    )
    out = formalizer_smt2_block(ctx, cfg=SmtPipelineConfig())
    assert "assert true" in out.lower()
    assert "system" in called
