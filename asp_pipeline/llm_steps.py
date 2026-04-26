"""Asp formalizer and critic: Gemini, prompts in ``asp_pipeline/prompts/``."""

from __future__ import annotations

import hashlib
from pathlib import Path

from asp_pipeline.clingo_check import strip_lp_fences
from asp_pipeline.config import AspPipelineConfig
from asp_pipeline.models import AspCriticContext, AspFormalizerContext

_PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    p = _PROMPT_DIR / name
    if not p.is_file():
        raise FileNotFoundError(f"missing prompt file: {p}")
    return p.read_text(encoding="utf-8")


def _formalizer_prompt_basename(cfg: AspPipelineConfig) -> str:
    """Single filename under ``prompts/``; no path separators or ``..``."""
    raw = (cfg.formalizer_prompt or "formalizer_new.md").strip() or "formalizer_new.md"
    if ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError(f"invalid formalizer prompt name (use basename only): {raw!r}")
    if Path(raw).name != raw:
        raise ValueError(f"invalid formalizer prompt name: {raw!r}")
    return raw


def formalizer_prompt_path(cfg: AspPipelineConfig) -> Path:
    name = _formalizer_prompt_basename(cfg)
    p = _PROMPT_DIR / name
    if not p.is_file():
        raise FileNotFoundError(f"formalizer prompt not found: {p}")
    return p


def formalizer_prompt_fingerprint(cfg: AspPipelineConfig) -> tuple[str, str]:
    """``(basename, sha256_hex)`` of the configured formalizer system prompt file."""
    p = formalizer_prompt_path(cfg)
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    return p.name, h


def build_formalizer_user_message(ctx: AspFormalizerContext) -> str:
    pol = ctx.policy_text if ctx.policy_text.strip() else "(empty - first policy commit)"
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
        "in_scope_lines (one per rule, stable order):",
    ]
    for ln in ctx.in_scope_lines:
        parts.append(ln)
    parts.append("</new_bundle>")
    if ctx.previous_lp_block is not None:
        parts.extend(
            [
                "",
                "<previous_attempt>",
                ctx.previous_lp_block,
                "</previous_attempt>",
            ]
        )
    if ctx.feedback:
        parts.extend(["", "<feedback>", ctx.feedback, "</feedback>"])
    parts.extend(["", "Produce the full .lp program for this bundle (see system prompt)."])
    return "\n".join(parts)


def build_critic_user_message(ctx: AspCriticContext) -> str:
    pol = ctx.policy_text if ctx.policy_text.strip() else "(empty - first policy commit)"
    parts = [
        "<existing_policy_model>",
        pol,
        "</existing_policy_model>",
        "",
        "<new_bundle_nl>",
        f"bundle_id: {ctx.bundle_id}",
        f"policy_path: {ctx.policy_path}",
        "in_scope_lines (WFM, one per rule):",
        ctx.in_scope_wfm_summary or "(none)",
        "</new_bundle_nl>",
        "",
        "<proposed_lp_block>",
        ctx.proposed_lp_block,
        "</proposed_lp_block>",
        "",
        "Return only the JSON object (see system prompt).",
    ]
    return "\n".join(parts)


def formalizer_lp_gemini(ctx: AspFormalizerContext, *, cfg: AspPipelineConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt(_formalizer_prompt_basename(cfg))
    user = build_formalizer_user_message(ctx)
    return gemini_complete(
        system_instruction=system,
        user_text=user,
        max_output_tokens=cfg.formalizer_max_output_tokens,
    )


def critic_json_gemini(ctx: AspCriticContext, *, cfg: AspPipelineConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt("critic.md")
    user = build_critic_user_message(ctx)
    return gemini_complete(
        system_instruction=system,
        user_text=user,
        max_output_tokens=cfg.critic_max_output_tokens,
    )
