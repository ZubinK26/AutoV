"""Repair agent (``prompts/repairer.md``). Gemini: same thinking as formalizer; Claude ignores ``thinking_level``."""

from __future__ import annotations

from nagv.agent_trace import emit_llm_trace_input, emit_llm_trace_output
from nagv.llm import NAGV_AGENT_THINKING_LEVEL, call_llm, nagv_gemini_model
from nagv.prompt_build import (
    extract_python_code,
    inject_repairer,
    is_abort_response,
    load_prompt,
    normalize_nagini_contracts_imports,
)


def repair_code(
    *,
    nl_ruleset: str,
    current_python: str,
    diagnostic: str,
    trace_step: str | None = None,
) -> tuple[str | None, str]:
    """
    Revise ``current_python`` from a **single** ``diagnostic`` and the original NL.
    Returns ``(python_source | None, raw_model_text)``.
    """
    template = load_prompt("repairer.md")
    filled = inject_repairer(template, nl_ruleset, current_python, diagnostic)
    user_msg = "Apply OUTPUT FORMAT from the system instructions."
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
