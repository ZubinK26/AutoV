"""Registry-stage Gemini agents: search expansion + structured gap extraction (M3)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path

from registry_stage.models import ENTRY_KINDS, StructuredGap

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

LlmComplete = Callable[[str, str], str]


def load_system_prompt(md_path: Path) -> str:
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"```\s*\n(.*?)```", raw, re.DOTALL)
    if not m:
        raise ValueError(f"No ``` fenced system block in {md_path}")
    return m.group(1).strip()


def parse_json_object(text: str) -> dict:
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", t, re.DOTALL)
    if m:
        t = m.group(1)
    else:
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            t = t[start : end + 1]
    return json.loads(t)


def _cap_phrases(phrases: list[str], *, max_phrases: int, max_chars: int) -> list[str]:
    out: list[str] = []
    for p in phrases:
        s = (p or "").strip()
        if not s:
            continue
        if len(s) > max_chars:
            s = s[:max_chars]
        out.append(s)
        if len(out) >= max_phrases:
            break
    return out


def expand_search_phrases_parsed(
    *,
    statement_nl: str,
    extra_context: str | None,
    llm_complete: LlmComplete,
) -> list[str]:
    """Phrases from the model after JSON parse and strip, **before** count/char caps (Lane A raw layer)."""
    path = PROMPTS_DIR / "registry_search_expand.md"
    system = load_system_prompt(path)
    payload = {
        "statement_nl": statement_nl.strip(),
        "extra_context": (extra_context or "")[:2000],
    }
    user = json.dumps(payload, ensure_ascii=False) + "\n\nRespond with JSON only: {\"phrases\": [\"...\", ...]}"
    raw_text = llm_complete(system, user)
    data = parse_json_object(raw_text)
    raw_list = data.get("phrases")
    if not isinstance(raw_list, list):
        return []
    return [str(x).strip() for x in raw_list if str(x).strip()]


def expand_search_phrases_with_raw(
    *,
    statement_nl: str,
    extra_context: str | None,
    llm_complete: LlmComplete,
    max_phrases: int,
    max_chars: int,
) -> tuple[list[str], list[str]]:
    """Returns ``(raw_phrases_pre_cap, capped_phrases_for_search)``."""
    raw = expand_search_phrases_parsed(
        statement_nl=statement_nl,
        extra_context=extra_context,
        llm_complete=llm_complete,
    )
    capped = _cap_phrases(list(raw), max_phrases=max_phrases, max_chars=max_chars)
    return raw, capped


def expand_search_phrases(
    *,
    statement_nl: str,
    extra_context: str | None,
    llm_complete: LlmComplete,
    max_phrases: int,
    max_chars: int,
) -> list[str]:
    _, capped = expand_search_phrases_with_raw(
        statement_nl=statement_nl,
        extra_context=extra_context,
        llm_complete=llm_complete,
        max_phrases=max_phrases,
        max_chars=max_chars,
    )
    return capped


def extract_structured_gaps(
    *,
    statement_nl: str,
    authoritative_registry_summary: str,
    llm_complete: LlmComplete,
) -> list[StructuredGap]:
    path = PROMPTS_DIR / "registry_gap_extract.md"
    system = load_system_prompt(path)
    payload = {
        "statement_nl": statement_nl.strip(),
        "authoritative_registry_coverage": authoritative_registry_summary[:8000],
    }
    user = (
        json.dumps(payload, ensure_ascii=False)
        + "\n\nRespond with JSON only: {\"gaps\": [{\"surface\": \"...\", \"kind\": \"sort|constant|function\", "
        '"arity_hint": null, "domain_hints": [], "notes": ""}, ...]}'
    )
    raw = llm_complete(system, user)
    data = parse_json_object(raw)
    raw_gaps = data.get("gaps")
    if not isinstance(raw_gaps, list):
        return []
    out: list[StructuredGap] = []
    for item in raw_gaps:
        if not isinstance(item, dict):
            continue
        surface = str(item.get("surface", "")).strip()
        kind = str(item.get("kind", "")).strip()
        if not surface or kind not in ENTRY_KINDS:
            continue
        ah = item.get("arity_hint")
        arity = int(ah) if isinstance(ah, int) else None
        dom = item.get("domain_hints")
        hints: tuple[str, ...] = ()
        if isinstance(dom, list):
            hints = tuple(str(x) for x in dom if str(x).strip())
        notes = str(item.get("notes", "") or "").strip()
        out.append(
            StructuredGap(
                surface=surface,
                kind=kind,
                arity_hint=arity,
                domain_hints=hints,
                notes=notes,
            )
        )
    return out


def resolve_registry_nl_parsed(
    *,
    statement_nl: str,
    authoritative_hits_context: str,
    gap_spans: list[str],
    structured_gaps: list[dict],
    llm_complete: LlmComplete,
    validation_feedback: str | None = None,
) -> dict:
    """Single structured resolve call; returns parsed JSON dict (``resolve_v1``)."""
    path = PROMPTS_DIR / "registry_resolve_automated.md"
    system = load_system_prompt(path)
    payload: dict = {
        "statement_nl": statement_nl.strip(),
        "authoritative_hits_context": authoritative_hits_context[:12000],
        "gap_spans": gap_spans[:200],
        "structured_gaps": structured_gaps[:80],
    }
    user = json.dumps(payload, ensure_ascii=False)
    if validation_feedback:
        user += (
            "\n\nThe previous JSON failed validation:\n"
            + validation_feedback[:4000]
            + "\n\nReturn a corrected JSON object only."
        )
    else:
        user += "\n\nReturn the JSON object only, no other text."
    raw = llm_complete(system, user)
    return parse_json_object(raw)


def default_gemini_complete(system: str, user: str) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    return gemini_complete(system_instruction=system, user_text=user)
