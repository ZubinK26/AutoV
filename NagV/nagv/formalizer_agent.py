"""Formalizer agent (``prompts/formalizer.md``)."""

from __future__ import annotations

from nagv.agent_trace import emit_llm_trace_input, emit_llm_trace_output
from nagv.llm import NAGV_AGENT_THINKING_LEVEL, call_llm, nagv_gemini_model
from nagv.prompt_build import (
    extract_python_code,
    inject_formalizer_base,
    inject_formalizer_with_feedback,
    is_abort_response,
    load_prompt,
    normalize_nagini_contracts_imports,
)


def formalize(
    nl_ruleset: str,
    feedback: str = "",
    *,
    trace_step: str | None = None,
) -> tuple[str | None, str]:
    """
    Returns ``(python_source | None, raw_model_text)``.
    ``None`` if abort / no extractable Python.
    """
    base = load_prompt("formalizer.md")
    filled = inject_formalizer_with_feedback(inject_formalizer_base(base, nl_ruleset), feedback)
    user_msg = "Respond per OUTPUT FORMAT in the system instructions."
    trace_path = None
    if trace_step:
        trace_path = emit_llm_trace_input(trace_step, filled, user_msg)
    try:
        raw = call_llm(
            system_instruction=filled,
            user_text=user_msg,
            model=nagv_gemini_model(),
            thinking_level=NAGV_AGENT_THINKING_LEVEL,
        )
    except BaseException as e:
        if trace_path is not None:
            emit_llm_trace_output(
                trace_path,
                f"<llm_call_raised: {type(e).__name__}: {e}>\n",
            )
        raise
    if trace_path is not None:
        emit_llm_trace_output(trace_path, raw)
    if is_abort_response(raw):
        return None, raw
    code = extract_python_code(raw)
    if not code:
        return None, raw
    code = normalize_nagini_contracts_imports(code)
    return code, raw
