from __future__ import annotations


def test_encodability_stack_includes_temporal_addendum() -> None:
    from pivot_pipeline.paths import read_pivot_encodability_prompt_stack

    stack = read_pivot_encodability_prompt_stack()
    assert "Temporal surrogates" in stack
    assert "T1" in stack and "T8" in stack


def test_extract_prompt_includes_stack() -> None:
    from pivot_pipeline.extract import _extract_prompt_template

    tmpl = _extract_prompt_template()
    assert "temporal_surrogates" in tmpl.lower() or "Temporal surrogates" in tmpl


def test_scope_rewriter_prompt_includes_stack() -> None:
    from pivot_pipeline.scope_rewriter_agent import load_scope_rewriter_system_prompt

    txt = load_scope_rewriter_system_prompt()
    assert "Temporal surrogates" in txt
