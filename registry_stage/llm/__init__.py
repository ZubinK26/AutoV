"""LLM utilities for registry stage (Gemini; M3 expansion + structured gaps)."""

from registry_stage.llm.agents import (
    default_gemini_complete,
    expand_search_phrases,
    extract_structured_gaps,
)
from registry_stage.llm.gemini_call import gemini_complete, load_repo_dotenv

__all__ = [
    "default_gemini_complete",
    "expand_search_phrases",
    "extract_structured_gaps",
    "gemini_complete",
    "load_repo_dotenv",
]
