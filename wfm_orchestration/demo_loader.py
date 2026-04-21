"""
Curated FOLIO / P-FOLIO / stress pools + manual word cap (**e2e G6 / G7**).

Loads example bodies from the same markdown files as ``run_wfm_folio_gemini.py``.
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent


def _load_run_wfm_folio_module():
    path = _REPO / "test_sets" / "scripts" / "run_wfm_folio_gemini.py"
    name = "run_wfm_folio_gemini"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    # Required so ``@dataclass`` can resolve string annotations during exec.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = None


def _folio_module():
    global _mod
    if _mod is None:
        _mod = _load_run_wfm_folio_module()
    return _mod


def word_count(text: str) -> int:
    """Whitespace-split word count (English-style)."""
    return len(text.split())


def load_demo_pool_config(path: Path | None = None) -> dict[str, Any]:
    p = path or Path(__file__).resolve().parent / "demo_curated_pools.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _all_curated_examples(cfg: dict[str, Any]) -> dict[str, Any]:
    """Map example_id -> Example dataclass from harness."""
    mod = _folio_module()
    folio_path = _REPO / cfg["sources"]["folio"]
    stress_path = _REPO / cfg["sources"]["stress"]
    out: dict[str, Any] = {}
    for e in mod.parse_folio_examples(folio_path):
        out[e.ex_id] = e
    for e in mod.parse_pfolio_examples(folio_path):
        out[e.ex_id] = e
    for e in mod.parse_stress_examples(stress_path):
        out[e.ex_id] = e
    return out


def compute_manual_word_limit(cfg: dict[str, Any] | None = None) -> int:
    """
    **G7:** ``max(word count across all curated example bodies) + manual_word_limit_extra``.
    """
    cfg = cfg or load_demo_pool_config()
    extra = int(cfg.get("manual_word_limit_extra", 15))
    ids: list[str] = []
    ids.extend(cfg["folio_example_ids"])
    ids.extend(cfg["pfolio_example_ids"])
    ids.extend(cfg["stress_example_ids"])
    by_id = _all_curated_examples(cfg)
    max_w = 0
    for ex_id in ids:
        ex = by_id.get(ex_id)
        if ex is None:
            raise KeyError(f"Example id not found in sources: {ex_id}")
        max_w = max(max_w, word_count(ex.text))
    return max_w + extra


def get_curated_example_text(ex_id: str, *, cfg: dict[str, Any] | None = None) -> str:
    """Return the rule body for a curated id (FOLIO, P-FOLIO, or stress)."""
    cfg = cfg or load_demo_pool_config()
    by_id = _all_curated_examples(cfg)
    ex = by_id.get(ex_id)
    if ex is None:
        raise KeyError(f"Unknown curated example id: {ex_id}")
    return ex.text


def text_for_demo_choice(
    choice: str,
    *,
    cfg: dict[str, Any] | None = None,
    rng: random.Random | None = None,
    exclude_ids: AbstractSet[str] | None = None,
) -> tuple[str, str]:
    """
    ``choice`` is ``folio`` | ``pfolio`` | ``stress``.

    Returns ``(example_id, body_text)``. ``exclude_ids`` shrinks the pool (e.g. after user rejects a pick).
    """
    cfg = cfg or load_demo_pool_config()
    rng = rng or random.Random()
    by_id = _all_curated_examples(cfg)
    if choice == "folio":
        pool = list(cfg["folio_example_ids"])
    elif choice == "pfolio":
        pool = list(cfg["pfolio_example_ids"])
    elif choice == "stress":
        pool = list(cfg["stress_example_ids"])
    else:
        raise ValueError(f"Unknown choice: {choice!r}")
    excl = exclude_ids or frozenset()
    pool = [x for x in pool if x not in excl]
    if not pool:
        raise ValueError("no curated examples left in this pool (all excluded)")
    ex_id = rng.choice(pool)
    ex = by_id[ex_id]
    return ex_id, ex.text


@dataclass(frozen=True)
class ManualInputRejected(Exception):
    word_count: int
    limit: int


def validate_manual_text(text: str, *, limit: int) -> None:
    """Raise ``ManualInputRejected`` if ``word_count(text)`` exceeds ``limit``."""
    wc = word_count(text.strip())
    if wc > limit:
        raise ManualInputRejected(word_count=wc, limit=limit)
