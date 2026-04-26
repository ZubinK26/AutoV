"""
Which runs can be scored **against a stored reference ASP** in the repo (SymTex, manifest, asp_nl index).

FOLIO / P-FOLIO / stress text examples have **narrative** bodies only unless you add a ``.lp`` path in
``wfm_ground_truth_asp_map.json``. Default WFM/ASP work should not burn API calls on the latter
unless you opt in.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MANIFEST_BASENAME = "wfm_ground_truth_asp_map.json"


def default_manifest_path(repo_root: Path) -> Path:
    return Path(__file__).resolve().parent / MANIFEST_BASENAME


def load_ground_truth_asp_map(repo_root: Path) -> dict[str, str]:
    """
    ``curated_id`` -> path string (absolute or relative to *repo_root*). Missing file or invalid JSON → empty.
    """
    p = default_manifest_path(repo_root)
    if not p.is_file():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    m = raw.get("curated_id_to_reference_lp")
    if not isinstance(m, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in m.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            out[k] = v
    return out


def resolve_reference_lp(repo_root: Path, path_s: str) -> Path:
    p = Path(path_s)
    if p.is_absolute():
        return p
    return (repo_root / p).resolve()


def curated_id_has_ground_truth_lp(
    repo_root: Path, ex_id: str, d: dict[str, str] | None = None
) -> bool:
    m = d if d is not None else load_ground_truth_asp_map(repo_root)
    rel = m.get(ex_id)
    if not rel:
        return False
    return resolve_reference_lp(repo_root, rel).is_file()


def symtex_paired_is_assessable(ex: object) -> bool:
    ref = getattr(ex, "reference_asp_program", None)
    return isinstance(ref, str) and bool(ref.strip())


def truth_assessment_symtex_paired(ex: object) -> dict[str, Any]:
    return {
        "assessable_against_stored_reference_asp": symtex_paired_is_assessable(ex),
        "category": "symtex_textual_symbolic_paired",
        "rationale": "Reference ASP is loaded from the paired symbolic JSONL in test_sets/.../aspbench/.../SymTex.",
    }


def truth_assessment_asp_nl_bench() -> dict[str, Any]:
    return {
        "assessable_against_stored_reference_asp": True,
        "category": "asp_nl_bench_index_row",
        "rationale": "Reference program is required to load a row in the user-provided problems JSONL.",
    }


def truth_assessment_manual() -> dict[str, Any]:
    return {
        "assessable_against_stored_reference_asp": False,
        "category": "manual_user_text",
        "rationale": "No in-repo reference LP unless you add one; suitable for ad-hoc exploration, not automatic scoring.",
    }


def truth_assessment_curated_wfm(
    ex_id: str, *, repo_root: Path, m: dict[str, str] | None = None
) -> dict[str, Any]:
    m = m if m is not None else load_ground_truth_asp_map(repo_root)
    if curated_id_has_ground_truth_lp(repo_root, ex_id, m):
        p = m.get(ex_id) or ""
        return {
            "assessable_against_stored_reference_asp": True,
            "category": "wfm_curated_with_manifest_reference_lp",
            "reference_lp_path": p,
        }
    return {
        "assessable_against_stored_reference_asp": False,
        "category": "wfm_curated_folio_pfolio_stress",
        "rationale": (
            f"No entry (or missing file) for {ex_id!r} in wfm_ground_truth_asp_map.json — "
            "WFM/ASP runs here do not have a checkable program for this id."
        ),
    }
