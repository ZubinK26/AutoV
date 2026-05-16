"""Shared Gemini + registry session setup for ``cli`` and ``demo_launcher``."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable

from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex

from wfm_orchestration.gemini_client import env_thinking_level


def load_dotenv_for_e2e() -> None:
    """Load repo-root ``.env`` so ``GEMINI_API_KEY`` matches other harnesses (before reading env)."""
    from registry_stage.llm.gemini_call import load_repo_dotenv

    load_repo_dotenv()


@dataclass(frozen=True)
class E2EContext:
    client: Any
    model: str
    temperature: float
    max_output_tokens: int
    thinking_level: Any
    registry_session: RegistrySession
    llm_complete: Callable[[str, str], str]


def build_llm_complete(*, mock_resolve: bool) -> Callable[[str, str], str]:
    def llm_complete(system: str, user: str) -> str:
        if mock_resolve:
            return json.dumps(
                {
                    "schema_version": "resolve_v1",
                    "registry_resolution_candidate_nl": "resolved (mock)",
                    "cited_entry_ids": [],
                    "needs_human_review": False,
                    "primary_review_reason": "NONE",
                    "confidence_tier": "high",
                    "llm_rationale_short": "mock",
                }
            )
        from registry_stage.llm.gemini_call import gemini_complete, load_repo_dotenv

        load_repo_dotenv()
        return gemini_complete(system_instruction=system, user_text=user)

    return llm_complete


def create_e2e_context(
    *,
    mock_resolve: bool = False,
    registry_session: RegistrySession | None = None,
    gemini_model_override: str | None = None,
    gemini_thinking_level_token: str | None = None,
) -> E2EContext:
    """Requires ``GEMINI_API_KEY`` when ``mock_resolve`` is False (WFM still calls Gemini)."""
    load_dotenv_for_e2e()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    from google import genai

    client = genai.Client(api_key=api_key)
    model = (gemini_model_override or os.environ.get("GEMINI_MODEL", "gemini-3.1-pro-preview")).strip()
    temperature = float(os.environ.get("GEMINI_TEMPERATURE", "0"))
    max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", "16384"))
    if gemini_thinking_level_token is not None and str(gemini_thinking_level_token).strip():
        from registry_stage.llm.gemini_call import _thinking_level_from_str

        tl = _thinking_level_from_str(str(gemini_thinking_level_token))
    else:
        tl = env_thinking_level()
    session = registry_session or RegistrySession(
        semantic_index=StubKeywordSemanticIndex(), index_preference="stub"
    )
    return E2EContext(
        client=client,
        model=model,
        temperature=temperature,
        max_output_tokens=max_out,
        thinking_level=tl,
        registry_session=session,
        llm_complete=build_llm_complete(mock_resolve=mock_resolve),
    )
