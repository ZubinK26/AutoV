"""Optional dumps of each LLM turn: system + user (input) and raw model text (output).

Tracing is **off** unless ``NAGV_AGENT_TRACE`` is set to a truthy value
(``1``, ``true``, ``yes``, ``on``). When on, writes under ``work_dir/agent_trace/``
as ``0001_step.txt``, … — each file contains input sections first, then
``--- model_output ---`` after the API returns.
"""

from __future__ import annotations

import os
from pathlib import Path

_root: Path | None = None
_seq: int = 0


def configure_agent_trace(work_dir: Path | None) -> None:
    """Call from ``run_nagv`` after ``work_dir`` is known."""
    global _root, _seq
    _seq = 0
    if work_dir is None:
        _root = None
        return
    raw = os.environ.get("NAGV_AGENT_TRACE", "").strip().lower()
    if raw not in ("1", "true", "yes", "on"):
        _root = None
        return
    _root = work_dir.resolve() / "agent_trace"
    _root.mkdir(parents=True, exist_ok=True)


def emit_llm_trace_input(step: str, system_instruction: str, user_text: str) -> Path | None:
    """Write input sections; returns path to append model output, or ``None`` if tracing disabled."""
    if _root is None:
        return None
    global _seq
    _seq += 1
    safe = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in step)[:180]
    path = _root / f"{_seq:04d}_{safe}.txt"
    path.write_text(
        "=== "
        + step
        + " ===\n\n--- system_instruction ---\n"
        + system_instruction
        + "\n\n--- user_text ---\n"
        + user_text
        + "\n\n--- model_output ---\n",
        encoding="utf-8",
    )
    return path


def emit_llm_trace_output(path: Path | None, raw_model_text: str) -> None:
    """Append model response (or error summary) to the trace file created by ``emit_llm_trace_input``."""
    if path is None or not path.is_file():
        return
    with path.open("a", encoding="utf-8") as f:
        f.write(raw_model_text)
        if not raw_model_text.endswith("\n"):
            f.write("\n")
