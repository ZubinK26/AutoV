"""Gemini calls for policy refinement (assessor, implementer, repair)."""

from __future__ import annotations

from pathlib import Path

from .config import RefinementConfig


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    p = _prompts_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"missing prompt file: {p}")
    return p.read_text(encoding="utf-8")


def maybe_truncate_for_assessor(
    *,
    nl_source: str,
    nl_digest: str,
    policy_text: str,
    limit: int,
) -> str:
    overhead = len(nl_source) + len(nl_digest) + 500
    if overhead + len(policy_text) <= limit:
        return policy_text
    budget = max(10_000, limit - overhead)
    half = budget // 2
    return (
        policy_text[:half]
        + "\n; --- [REFINEMENT assessor: middle of policy truncated for context] ---\n"
        + policy_text[-half:]
    )


def build_assessor_user_message(
    *,
    nl_source: str,
    nl_digest: str,
    policy_text: str,
    run_id: str,
) -> str:
    parts = [
        "<nl_source>",
        nl_source,
        "</nl_source>",
        "",
        "<nl_numbered_digest>",
        nl_digest,
        "</nl_numbered_digest>",
        "",
        "<policy_model_smt2>",
        policy_text,
        "</policy_model_smt2>",
        "",
        "<task>",
        f"run_id: {run_id}",
        "Compare NL to SMT and output exactly one JSON object per the system prompt schema.",
        "no markdown fences.",
        "</task>",
    ]
    return "\n".join(parts)


def build_implementer_user_message(
    *,
    recommendations_json: str,
    policy_text: str,
    nl_excerpt: str,
) -> str:
    parts = [
        "<recommendations_json>",
        recommendations_json,
        "</recommendations_json>",
        "",
        "<policy_model_smt2>",
        policy_text,
        "</policy_model_smt2>",
        "",
        "<nl_source>",
        nl_excerpt,
        "</nl_source>",
        "",
        "<constraints>",
        "Preserve (set-logic) line if present. Preserve all ; Bundle:, ; Rule:, ; NL: headers. Add REFINE comments per system prompt.",
        "</constraints>",
        "",
        "Output the JSON object now.",
    ]
    return "\n".join(parts)


def build_repair_user_message(
    *,
    full_policy: str,
    refine_regions: str,
    syntax_error: str | None,
    unsat_detail: str | None,
    objections_json: str | None,
) -> str:
    parts = [
        "<full_policy>",
        full_policy,
        "</full_policy>",
        "",
        "<refine_regions>",
        refine_regions or "(none extracted)",
        "</refine_regions>",
        "",
        "<syntax_error>",
        syntax_error or "",
        "</syntax_error>",
        "",
        "<unsat_report>",
        unsat_detail or "",
        "</unsat_report>",
        "",
        "<critic_objections>",
        objections_json or "",
        "</critic_objections>",
        "",
        "<output_mode>full</output_mode>",
        "Output the entire corrected policy as raw SMT-LIB text only (no markdown, no JSON).",
    ]
    return "\n".join(parts)


def assessor_gemini(user_text: str, *, cfg: RefinementConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt("assessor_v1.md")
    return gemini_complete(
        system_instruction=system,
        user_text=user_text,
        max_output_tokens=cfg.assessor_max_output_tokens,
    )


def implementer_gemini(user_text: str, *, cfg: RefinementConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt("implementer_v1.md")
    return gemini_complete(
        system_instruction=system,
        user_text=user_text,
        max_output_tokens=cfg.implementer_max_output_tokens,
    )


def repair_formalizer_gemini(user_text: str, *, cfg: RefinementConfig) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    system = load_prompt("repair_formalizer_v1.md")
    return gemini_complete(
        system_instruction=system,
        user_text=user_text,
        max_output_tokens=cfg.repair_max_output_tokens,
    )
