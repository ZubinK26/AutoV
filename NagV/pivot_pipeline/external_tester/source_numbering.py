"""Convert raw text chunks to numbered line envelopes."""

from __future__ import annotations

import hashlib

from pivot_pipeline.external_tester.schemas import ExternalSourceEnvelope


def raw_text_to_envelope(text: str, *, source_id: str | None = None) -> ExternalSourceEnvelope:
    """Split on newlines; preserve line content (no strip of empty trailing-only)."""
    lines = text.splitlines()
    if not lines and text:
        lines = [text]
    sid = source_id or hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return ExternalSourceEnvelope(
        source_id=sid,
        line_count=len(lines),
        lines=lines,
    )


__all__ = ["raw_text_to_envelope"]
