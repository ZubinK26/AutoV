"""Atomic write for `policy_model.smt2` (`.new` + rename)."""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_path = path.with_name(path.name + ".new")
    new_path.write_text(content, encoding=encoding)
    os.replace(new_path, path)
