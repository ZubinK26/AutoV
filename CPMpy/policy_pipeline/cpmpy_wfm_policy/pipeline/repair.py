"""Repair-loop helpers: diagnoser-driven hints for the formalizer (slice 3)."""

from __future__ import annotations


def fallback_repair_hint(raw_error: str) -> str:
    """When no diagnoser LLM is configured, nudge the formalizer with the raw error."""
    return (
        "Previous attempt failed. Fix the output so it matches the JSON schema and validates. "
        f"Error: {raw_error}"
    )
