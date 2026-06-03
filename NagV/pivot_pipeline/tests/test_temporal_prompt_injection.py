from __future__ import annotations


def test_encodability_stack_includes_temporal_addendum() -> None:
    from pivot_pipeline.paths import read_pivot_encodability_prompt_stack

    stack = read_pivot_encodability_prompt_stack()
    assert "Temporal surrogates" in stack
    assert "T1" in stack and "T8" in stack
    assert "Subjective assessment" in stack
    assert "S1" in stack and "invented metrics" in stack.lower()


def test_extract_prompt_includes_stack() -> None:
    from pivot_pipeline.extract import _extract_prompt_template

    tmpl = _extract_prompt_template()
    assert "temporal_surrogates" in tmpl.lower() or "Temporal surrogates" in tmpl


def test_scope_rewriter_prompt_includes_stack() -> None:
    from pivot_pipeline.scope_rewriter_agent import load_scope_rewriter_system_prompt

    txt = load_scope_rewriter_system_prompt()
    assert "Temporal surrogates" in txt
    assert "subjective_assessment" in txt


def test_assessment_mode_for_bool_surrogate_names() -> None:
    from pivot_pipeline.external_tester.variable_catalog import assessment_mode_for_var

    assert assessment_mode_for_var("candidate_can_write_technical_english", "bool") == "subjective_llm"
    assert assessment_mode_for_var("years_backend_experience", "int") is None
