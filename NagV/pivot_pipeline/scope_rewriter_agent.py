"""Pre-WFM Scope Rewriter: reference NL → pivot-aligned plain rules + sidecar JSON."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field, field_validator

from pivot_pipeline.llm import get_pivot_gemini_model, get_pivot_gemini_thinking_level_str
from pivot_pipeline.paths import read_v1_policy_encodability_contract
from registry_stage.llm.gemini_call import gemini_complete

SCHEMA_VERSION = "scope_rewriter_sidecar_v1"
PROMPT_REL = Path("prompts") / "scope_rewriter_pre_wfm.md"

INPUT_MODE_REFERENCE_CORPUS = "reference_corpus"
INPUT_MODE_POLICY_INTENT_SPEC = "policy_intent_spec"
VALID_INPUT_MODES = frozenset({INPUT_MODE_REFERENCE_CORPUS, INPUT_MODE_POLICY_INTENT_SPEC})


def normalize_input_mode(raw: str | None) -> str:
    """CLI wins when ``raw`` is non-empty; else ``SCOPE_REWRITER_INPUT_MODE``; else reference corpus."""
    if raw is not None and str(raw).strip():
        s = str(raw).strip().lower().replace("-", "_")
        if s in VALID_INPUT_MODES:
            return s
        raise ValueError(
            f"invalid input_mode {raw!r}; expected one of {sorted(VALID_INPUT_MODES)}"
        )
    env = (os.getenv("SCOPE_REWRITER_INPUT_MODE") or "").strip().lower().replace("-", "_")
    if env in VALID_INPUT_MODES:
        return env
    return INPUT_MODE_REFERENCE_CORPUS


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _coerce_string_list(v: Any) -> list[str]:
    """Normalize list fields when the model emits null, the string 'None', or a bare string."""
    if v is None:
        return []
    if isinstance(v, list):
        out: list[str] = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if not s or s.lower() == "none":
                continue
            out.append(s)
        return out
    if isinstance(v, str):
        s = v.strip()
        if not s or s.lower() == "none":
            return []
        return [s]
    return []


def _coerce_int_list(v: Any) -> list[int]:
    if v is None:
        return []
    if isinstance(v, list):
        out: list[int] = []
        for x in v:
            if x is None:
                continue
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out
    return []


class PartialRewrite(BaseModel):
    approximate_line_span: str = ""
    reason: str = ""
    nearest_rewrite_note: str = ""


class EnumerationCompressed(BaseModel):
    topic: str = ""
    kept: str = ""
    dropped_facets: list[str] = Field(default_factory=list)

    @field_validator("dropped_facets", mode="before")
    @classmethod
    def _coerce_dropped_facets(cls, v: Any) -> list[str]:
        return _coerce_string_list(v)


class ScopeRewriterLLMOutput(BaseModel):
    schema_version: str
    plain_rules: str
    fidelity_summary: str = ""
    strict_equivalence_achievable: bool = True
    partial_rewrites: list[PartialRewrite] = Field(default_factory=list)
    semantic_deltas: list[str] = Field(default_factory=list)
    ready_for_wfm: bool = False
    no_further_agent_changes_recommended: bool = False
    modality_notes: list[str] = Field(default_factory=list)
    omissions_check: list[str] = Field(default_factory=list)
    enumerations_compressed: list[EnumerationCompressed] = Field(default_factory=list)
    line_encodability_tags: list[str] = Field(default_factory=list)
    high_friction_line_indices: list[int] = Field(default_factory=list)
    suggested_human_review_focus: list[str] = Field(default_factory=list)

    @field_validator(
        "semantic_deltas",
        "modality_notes",
        "omissions_check",
        "line_encodability_tags",
        "suggested_human_review_focus",
        mode="before",
    )
    @classmethod
    def _coerce_str_lists(cls, v: Any) -> list[str]:
        return _coerce_string_list(v)

    @field_validator("high_friction_line_indices", mode="before")
    @classmethod
    def _coerce_high_friction(cls, v: Any) -> list[int]:
        return _coerce_int_list(v)


def normalize_plain_rules(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines) + ("\n" if lines else "")


def extract_json_object(raw: str) -> dict[str, Any]:
    """Parse a single JSON object from model output (strip ```json fences if present)."""
    s = raw.strip()
    if not s:
        raise ValueError("empty model response")
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```\s*$", s, re.IGNORECASE)
    if fence:
        s = fence.group(1).strip()
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(s[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def parse_llm_output(raw: str) -> ScopeRewriterLLMOutput:
    data = extract_json_object(raw)
    return ScopeRewriterLLMOutput.model_validate(data)


def load_scope_rewriter_system_prompt() -> str:
    base_path = Path(__file__).resolve().parent / PROMPT_REL
    if not base_path.is_file():
        raise FileNotFoundError(f"Scope Rewriter prompt missing: {base_path}")
    base = base_path.read_text(encoding="utf-8")
    contract = read_v1_policy_encodability_contract()
    return (
        f"{base}\n\n---\n\n## Pivot v1 encodability contract (injected)\n\n{contract}\n"
    )


def build_user_initial(*, reference_text: str, input_mode: str = INPUT_MODE_REFERENCE_CORPUS) -> str:
    mode = normalize_input_mode(input_mode)
    body_label = (
        "Reference document (full text)"
        if mode == INPUT_MODE_REFERENCE_CORPUS
        else "Policy intent specification (guardrails and constraints)"
    )
    return (
        "## Mode\ninitial_rewrite\n\n"
        f"## Scope Rewriter input_mode\n{mode}\n\n"
        f"## {body_label}\n\n"
        f"{reference_text.strip()}\n"
    )


def build_user_review(
    *,
    reference_text: str,
    current_plain_rules: str,
    prior_sidecar: dict[str, Any] | None,
    operator_note: str,
    input_mode: str = INPUT_MODE_REFERENCE_CORPUS,
) -> str:
    mode = normalize_input_mode(input_mode)
    auth_label = (
        "Reference document (unchanged authority)"
        if mode == INPUT_MODE_REFERENCE_CORPUS
        else "Policy intent specification (unchanged authority)"
    )
    prior_json = json.dumps(prior_sidecar or {}, indent=2, ensure_ascii=False)
    note = operator_note.strip() or "(none)"
    return (
        "## Mode\nhuman_review_followup\n\n"
        f"## Scope Rewriter input_mode\n{mode}\n\n"
        f"## {auth_label}\n\n"
        f"{reference_text.strip()}\n\n"
        "## Current candidate plain rules (possibly human-edited)\n\n"
        f"{current_plain_rules.rstrip()}\n\n"
        "## Previous agent round JSON\n\n"
        f"{prior_json}\n\n"
        "## Operator note for this round\n\n"
        f"{note}\n"
    )


def _scope_rewriter_model() -> str:
    return os.getenv("SCOPE_REWRITER_MODEL", "").strip() or get_pivot_gemini_model()


def _scope_rewriter_temperature() -> float:
    raw = os.getenv("SCOPE_REWRITER_TEMPERATURE", "").strip()
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return float(os.getenv("GEMINI_TEMPERATURE", "0").strip() or "0")


def _scope_rewriter_max_out() -> int:
    raw = os.getenv("SCOPE_REWRITER_MAX_OUTPUT_TOKENS", "").strip()
    if raw:
        try:
            return max(1024, int(raw))
        except ValueError:
            pass
    raw2 = os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "32768").strip()
    try:
        return max(1024, int(raw2))
    except ValueError:
        return 32768


def _scope_rewriter_thinking() -> str | None:
    t = os.getenv("SCOPE_REWRITER_THINKING_LEVEL", "").strip()
    if t:
        return t
    return get_pivot_gemini_thinking_level_str() or None


def call_scope_rewriter_llm(*, system_instruction: str, user_text: str) -> str:
    # application/json avoids invalid JSON from raw newlines inside string fields (e.g. plain_rules).
    return gemini_complete(
        system_instruction=system_instruction,
        user_text=user_text,
        model=_scope_rewriter_model(),
        thinking_level=_scope_rewriter_thinking(),
        max_output_tokens=_scope_rewriter_max_out(),
        temperature=_scope_rewriter_temperature(),
        response_mime_type="application/json",
    )


@dataclass
class ScopeRewriterResult:
    nl_path: Path
    sidecar_path: Path
    record: dict[str, Any]
    parsed: ScopeRewriterLLMOutput


def _append_log(work_dir: Path, record: dict[str, Any]) -> None:
    log_path = work_dir / "scope_rewriter_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "saved_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **{k: record[k] for k in ("round_index", "reference_sha256", "output_sha256", "input_mode") if k in record},
        "ready_for_wfm": record.get("ready_for_wfm"),
        "strict_equivalence_achievable": record.get("strict_equivalence_achievable"),
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_scope_rewriter_round(
    *,
    reference_path: Path,
    work_dir: Path,
    round_index: int,
    prior_nl_path: Path | None,
    prior_sidecar: dict[str, Any] | None,
    operator_note: str,
    # "reference" == path to Markdown/text for either mode (naming legacy)
    system_instruction: str,
    input_mode: str = INPUT_MODE_REFERENCE_CORPUS,
    llm_fn: Callable[[str, str], str] | None = None,
) -> ScopeRewriterResult:
    """
    One agent turn. ``prior_nl_path`` / ``prior_sidecar`` set for review rounds; else initial.
    """
    reference_text = reference_path.read_text(encoding="utf-8")
    ref_hash = _sha256_file(reference_path)
    mode_eff = normalize_input_mode(input_mode)

    llm = llm_fn or (lambda si, ut: call_scope_rewriter_llm(system_instruction=si, user_text=ut))

    if prior_nl_path is None:
        user_text = build_user_initial(reference_text=reference_text, input_mode=mode_eff)
    else:
        current_plain = prior_nl_path.read_text(encoding="utf-8")
        user_text = build_user_review(
            reference_text=reference_text,
            current_plain_rules=current_plain,
            prior_sidecar=prior_sidecar,
            operator_note=operator_note,
            input_mode=mode_eff,
        )

    raw = llm(system_instruction, user_text)
    parsed = parse_llm_output(raw)
    if parsed.schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"unexpected schema_version {parsed.schema_version!r}; require {SCHEMA_VERSION!r}"
        )

    body = normalize_plain_rules(parsed.plain_rules)
    out_dir = work_dir / "scope_rewriter"
    hist = out_dir / "history"
    out_dir.mkdir(parents=True, exist_ok=True)
    hist.mkdir(parents=True, exist_ok=True)

    latest_nl = out_dir / "latest.nl"
    latest_json = out_dir / "latest.json"

    if latest_nl.is_file():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = hist / f"before_round_{round_index}_{ts}.nl"
        try:
            bak.write_text(latest_nl.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass

    latest_nl.write_text(body, encoding="utf-8")
    out_hash = _sha256_text(body)

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "reference_path": str(reference_path.resolve()),
        "reference_sha256": ref_hash,
        "input_mode": mode_eff,
        "output_sha256": out_hash,
        "round_index": round_index,
        "fidelity_summary": parsed.fidelity_summary,
        "strict_equivalence_achievable": parsed.strict_equivalence_achievable,
        "partial_rewrites": [pr.model_dump() for pr in parsed.partial_rewrites],
        "semantic_deltas": list(parsed.semantic_deltas),
        "modality_notes": list(parsed.modality_notes),
        "omissions_check": list(parsed.omissions_check),
        "enumerations_compressed": [
            ec.model_dump() for ec in parsed.enumerations_compressed
        ],
        "line_encodability_tags": list(parsed.line_encodability_tags),
        "high_friction_line_indices": list(parsed.high_friction_line_indices),
        "suggested_human_review_focus": list(parsed.suggested_human_review_focus),
        "ready_for_wfm": parsed.ready_for_wfm,
        "no_further_agent_changes_recommended": parsed.no_further_agent_changes_recommended,
        "plain_rules": body,
        "model_metadata": {
            "provider": "google_genai",
            "model": _scope_rewriter_model(),
            "temperature": _scope_rewriter_temperature(),
        },
    }
    latest_json.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    hist_json = hist / f"round_{round_index}.json"
    hist_nl = hist / f"round_{round_index}.nl"
    hist_json.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    hist_nl.write_text(body, encoding="utf-8")

    _append_log(work_dir, record)

    return ScopeRewriterResult(
        nl_path=latest_nl,
        sidecar_path=latest_json,
        record=record,
        parsed=parsed,
    )


def max_rounds_default() -> int:
    raw = os.getenv("SCOPE_REWRITER_MAX_ROUNDS", "20").strip()
    try:
        return max(1, min(int(raw), 100))
    except ValueError:
        return 20


__all__ = [
    "SCHEMA_VERSION",
    "INPUT_MODE_POLICY_INTENT_SPEC",
    "INPUT_MODE_REFERENCE_CORPUS",
    "VALID_INPUT_MODES",
    "EnumerationCompressed",
    "PartialRewrite",
    "ScopeRewriterLLMOutput",
    "ScopeRewriterResult",
    "build_user_initial",
    "build_user_review",
    "call_scope_rewriter_llm",
    "extract_json_object",
    "load_scope_rewriter_system_prompt",
    "max_rounds_default",
    "normalize_input_mode",
    "normalize_plain_rules",
    "parse_llm_output",
    "run_scope_rewriter_round",
]
