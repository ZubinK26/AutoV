"""Critic agent (``prompts/critic.md``). Gemini: ``NAGV_CRITIC_THINKING_LEVEL`` (``high``), not the agent default."""

from __future__ import annotations

from nagv.agent_trace import emit_llm_trace_input, emit_llm_trace_output
from nagv.llm import NAGV_CRITIC_THINKING_LEVEL, call_llm, nagv_critic_gemini_model
from nagv.prompt_build import inject_critic, load_prompt


def critique(*, nl_ruleset: str, python_code: str, trace_step: str | None = None) -> str:
    template = load_prompt("critic.md")
    filled = inject_critic(template, nl_ruleset, python_code)
    user_msg = "Apply the audit protocol and respond in the required OUTPUT FORMAT only."
    trace_path = None
    if trace_step:
        trace_path = emit_llm_trace_input(trace_step, filled, user_msg)
    try:
        raw = call_llm(
            system_instruction=filled,
            user_text=user_msg,
            model=nagv_critic_gemini_model(),
            thinking_level=NAGV_CRITIC_THINKING_LEVEL,
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
    return raw
