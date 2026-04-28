"""Formalizer and critic LLM steps (Gemini); prompts loaded from `smt_pipeline/prompts/`."""

from __future__ import annotations

from pathlib import Path

from .config import SmtPipelineConfig
from .models import CriticContext, FormalizerContext


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    p = _prompts_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"missing prompt file: {p}")
    return p.read_text(encoding="utf-8")


def build_formalizer_user_message(ctx: FormalizerContext) -> str:
    """Tagged layout must stay aligned with ``prompts/formalizer_v3.md`` § User message format."""
    pol = ctx.policy_text if ctx.policy_text.strip() else "(empty — first commit)"
    parts = [
        "<existing_policy_model>",
        pol,
        "</existing_policy_model>",
        "",
        "<new_bundle>",
        f"bundle_id: {ctx.bundle_id}",
        f"policy_path: {ctx.policy_path}",
        f"attempt_index: {ctx.attempt_index}",
        f"existing_rule_count_in_policy_file: {ctx.existing_rule_count}",
        "in_scope_lines (one line per rule, stable order):",
    ]
    for ln in ctx.in_scope_lines:
        parts.append(ln)
    parts.append("</new_bundle>")
    if ctx.previous_smt2_block is not None:
        parts.extend(
            [
                "",
                "<previous_attempt>",
                ctx.previous_smt2_block,
                "</previous_attempt>",
            ]
        )
    if ctx.critic_objections:
        parts.extend(
            [
                "",
                "<feedback>",
                ctx.critic_objections,
                "</feedback>",
            ]
        )
    parts.extend(["", "Produce the full SMT-LIB block for this bundle now (see system prompt)."])
    return "\n".join(parts)


def formalizer_smt2_block_gemini(ctx: FormalizerContext, *, cfg: SmtPipelineConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt("formalizer_v3.md")
    user = build_formalizer_user_message(ctx)
    return gemini_complete(
        system_instruction=system,
        user_text=user,
        max_output_tokens=cfg.formalizer_max_output_tokens,
    )


def build_critic_user_message(ctx: CriticContext) -> str:
    """Tagged layout must stay aligned with ``prompts/critic_v3.md`` § User message format."""
    pol = ctx.policy_text if ctx.policy_text.strip() else "(empty — first commit)"
    parts = [
        "<existing_policy_model>",
        pol,
        "</existing_policy_model>",
        "",
        "<new_bundle_nl>",
        f"bundle_id: {ctx.bundle_id}",
        f"policy_path: {ctx.policy_path}",
        "in_scope_lines (WFM NL, one line per rule):",
        ctx.in_scope_wfm_summary or "(none)",
        "</new_bundle_nl>",
        "",
        "<proposed_smtlib_block>",
        ctx.proposed_smt2_block,
        "</proposed_smtlib_block>",
        "",
        "Review the proposed block against the existing model and NL. Produce your JSON verdict now (see system prompt).",
    ]
    return "\n".join(parts)


def critic_json_gemini(ctx: CriticContext, *, cfg: SmtPipelineConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt("critic_v3.md")
    user = build_critic_user_message(ctx)
    return gemini_complete(
        system_instruction=system,
        user_text=user,
        max_output_tokens=cfg.critic_max_output_tokens,
    )
