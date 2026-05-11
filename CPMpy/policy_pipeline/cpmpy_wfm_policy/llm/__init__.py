"""LLM call contract for the CPMpy policy pipeline."""

from __future__ import annotations

from typing import Callable, Protocol


class LLMCompleteFn(Protocol):
    def __call__(self, *, system_instruction: str, user_text: str) -> str:
        """Return raw model text (no enforced JSON except by formalizer prompts)."""


FormalizerLLM = Callable[..., str]
