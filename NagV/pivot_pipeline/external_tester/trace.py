"""Append-only trace for external tester rounds."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_trace(work_dir: Path, event: dict[str, Any]) -> None:
    path = work_dir / "external_tester_trace.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


__all__ = ["append_trace"]
