"""Load Gemini call helpers from ``test_sets/scripts/run_wfm_folio_gemini.py`` (single source of truth)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_folio_module():
    repo = Path(__file__).resolve().parent.parent
    path = repo / "test_sets" / "scripts" / "run_wfm_folio_gemini.py"
    name = "run_wfm_folio_gemini"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    # Required so @dataclass can resolve cls.__module__ during exec (Python 3.12+).
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = None


def get_gemini_module():
    global _mod
    if _mod is None:
        _mod = _load_folio_module()
    return _mod


def call_gemini(client, **kwargs):
    return get_gemini_module().call_gemini(client, **kwargs)


def env_thinking_level():
    return get_gemini_module().env_thinking_level()


def model_supports_thinking_config(model: str) -> bool:
    """Whether the loaded Gemini helper will attach ``ThinkingConfig`` for this model id."""
    return get_gemini_module().model_supports_thinking_config(model)
