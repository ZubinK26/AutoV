"""Repo root and NagV asset paths (NagV package lives under ``<repo>/NagV/nagv/``)."""

from __future__ import annotations

from pathlib import Path

_PKG = Path(__file__).resolve().parent
NAGV_DIR = _PKG.parent
REPO_ROOT = NAGV_DIR.parent
PROMPTS_DIR = NAGV_DIR / "prompts"
