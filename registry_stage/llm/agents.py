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


def expand_search_phrases(
    *,
    statement_nl: str,
    extra_context: str | None,
    llm_complete: LlmComplete,
    max_phrases: int,
    max_chars: int,
) -> list[str]:
    path = PROMPTS_DIR / "registry_search_expand.md"
    system = load_system_prompt(path)
    payload = {
        "statement_nl": statement_nl.strip(),
        "extra_context": (extra_context or "")[:2000],
    }
    user = json.dumps(payload, ensure_ascii=False) + "\n\nRespond with JSON only: {\"phrases\": [\"...\", ...]}"
    raw = llm_complete(system, user)
    data = parse_json_object(raw)
    raw_list = data.get("phrases")
    if not isinstance(raw_list, list):
        return []
    phrases = [str(x).strip() for x in raw_list if str(x).strip()]
    return _cap_phrases(phrases, max_phrases=max_phrases, max_chars=max_chars)


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


def default_gemini_complete(system: str, user: str) -> str:
    from registry_stage.llm.gemini_call import gemini_complete

    return gemini_complete(system_instruction=system, user_text=user)
