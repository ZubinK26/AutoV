"""Load prompts and append JSONL audit lines for Phase 0."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

from cpmpy_wfm_policy.llm import FormalizerLLM

T = TypeVar("T")


def prompts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "llm" / "prompts"


def extract_system_prompt_from_phase0_md(text: str) -> str:
    """First fenced block under ``## System prompt``; otherwise full file."""
    marker = "## System prompt"
    if marker not in text:
        return text.strip()
    rest = text.split(marker, 1)[1]
    start = rest.find("```")
    if start < 0:
        return rest.strip()
    inner = rest[start + 3 :]
    inner = inner.lstrip()
    # drop optional language tag on same line as opening fence
    first_nl = inner.find("\n")
    if first_nl != -1 and not inner[:first_nl].strip().startswith(
        ("You ", "You\n", "Your ", "{")
    ):
        first_line = inner[:first_nl].strip()
        if first_line and not first_line.startswith("{"):
            inner = inner[first_nl + 1 :]
    end = inner.find("```")
    if end < 0:
        return inner.strip()
    return inner[:end].strip()


def load_phase0_system_prompt(filename: str) -> str:
    p = prompts_dir() / filename
    if not p.is_file():
        raise FileNotFoundError(f"missing Phase 0 prompt: {p}")
    return extract_system_prompt_from_phase0_md(p.read_text(encoding="utf-8"))


def load_prompt_md(name: str) -> str:
    p = prompts_dir() / name
    if not p.is_file():
        raise FileNotFoundError(f"missing prompt file: {p} (add Phase 0 prompt artifact)")
    return p.read_text(encoding="utf-8")


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_llm_event(
    path: Path,
    *,
    event: str,
    role: str,
    latency_s: float,
    model: str | None,
    user_excerpt: str,
    raw_response_excerpt: str,
    extra: dict[str, Any] | None = None,
) -> None:
    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "role": role,
        "latency_s": round(latency_s, 3),
        "model": model,
        "user_excerpt": user_excerpt[:4000],
        "raw_response_excerpt": raw_response_excerpt[:8000],
    }
    if extra:
        rec["extra"] = extra
    append_jsonl(path, rec)


def call_llm_logged(
    llm: FormalizerLLM,
    *,
    log_path: Path,
    role: str,
    system_instruction: str,
    user_text: str,
    model_tag: str | None = None,
) -> str:
    t0 = time.perf_counter()
    raw = llm(system_instruction=system_instruction, user_text=user_text)
    log_llm_event(
        log_path,
        event="llm_call",
        role=role,
        latency_s=time.perf_counter() - t0,
        model=model_tag,
        user_excerpt=user_text,
        raw_response_excerpt=raw,
    )
    return raw


def retry_json_parse(
    fn: Callable[[], T],
    *,
    max_attempts: int,
    log_path: Path,
    role: str,
    on_fail_message: str,
) -> T:
    last_err: Exception | None = None
    for attempt in range(max(1, max_attempts)):
        try:
            return fn()
        except Exception as e:
            last_err = e
            append_jsonl(
                log_path,
                {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "event": "json_retry",
                    "role": role,
                    "attempt": attempt + 1,
                    "error": str(e),
                    "message": on_fail_message,
                },
            )
    assert last_err is not None
    raise last_err
