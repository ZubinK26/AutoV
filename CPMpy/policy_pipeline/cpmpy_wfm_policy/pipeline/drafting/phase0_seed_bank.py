"""Curated few-shot seeds for Phase 0 agents (Sig_Agents README)."""

from __future__ import annotations

from pathlib import Path

from cpmpy_wfm_policy.pipeline.drafting.phase0_io import prompts_dir


def load_seed_reference_signature_text() -> str:
    """Concatenate ``seed_signatures/*.py`` (e.g. refund_example). Empty if absent."""
    d = prompts_dir() / "seed_signatures"
    if not d.is_dir():
        return ""
    parts: list[str] = []
    for p in sorted(d.glob("*.py")):
        parts.append(f"# --- reference: {p.name} ---\n")
        parts.append(p.read_text(encoding="utf-8").rstrip())
        parts.append("")
    return "\n".join(parts).strip()


def load_seed_reference_glossary_text() -> str:
    """Concatenate ``seed_glossaries/*.yaml`` for Glossary Drafter few-shots."""
    d = prompts_dir() / "seed_glossaries"
    if not d.is_dir():
        return ""
    parts: list[str] = []
    for p in sorted(d.glob("*.yaml")):
        parts.append(f"# --- reference glossary: {p.name} ---\n")
        parts.append(p.read_text(encoding="utf-8").rstrip())
        parts.append("")
    return "\n".join(parts).strip()
