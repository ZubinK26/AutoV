"""
Shared discovery for SymTex (NL + reference in ASPBench) handoffs and asp_pipeline completion state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DEFAULT_BUNDLE_OUT = Path("bundles") / "asp_from_wfm"


def is_symtex_wfm_bundle_id(bundle_id: str) -> bool:
    return bool(bundle_id) and bundle_id.startswith("symtex_batch_")


def looks_like_symtex_nl_bench_body(text: str) -> bool:
    """
    WFM handoffs from :func:`symtex_format_nl` in ``asp_demo_sources`` use a fixed lead-in
    and quoted Facts/Rules. Used to match nl–asp-benchmark handoffs in ``bundles/wfm_artifacts``.
    """
    t = (text or "").lstrip()
    return t.startswith("The following facts and rules are quoted verbatim from the benchmark instance.")


def load_handoff_bundle_id(path: Path) -> str:
    d = json.loads(path.read_text(encoding="utf-8"))
    b = d.get("bundle_id")
    if not isinstance(b, str) or not b.strip():
        raise ValueError(f"Missing bundle_id in {path}")
    return b


def is_asp_pipeline_committed(*, bundle_out_dir: Path, bundle_id: str) -> bool:
    """``bundles/asp_from_wfm/<bundle_id>.json`` exists with committed asp_clincon run."""
    f = bundle_out_dir / f"{bundle_id}.json"
    if not f.is_file():
        return False
    try:
        r: dict[str, Any] = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return r.get("pipeline_status") == "committed" and r.get("pipeline_kind") == "asp_clincon"


def iter_symtex_ground_truth_handoff_paths(
    handoff_dir: Path,
    *,
    glob: str = "*.json",
) -> list[Path]:
    """
    Handoffs that look like WFM over SymTex (ground-truth available in ASPBench):
    - JSON has ``bundle_id`` starting with ``symtex_batch_``
    - ``user_original_input`` has the SymTex benchmark banner (when present in file).
    """
    if not handoff_dir.is_dir():
        return []
    out: list[Path] = []
    for p in sorted(handoff_dir.glob(glob)):
        if "manifest" in p.name.lower():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(d, dict):
            continue
        bid = d.get("bundle_id")
        if not (isinstance(bid, str) and is_symtex_wfm_bundle_id(bid)):
            continue
        body = d.get("user_original_input")
        if isinstance(body, str) and not looks_like_symtex_nl_bench_body(body):
            continue
        out.append(p)
    return out


def pending_formalize_symtex_handoffs(
    *,
    repo_root: Path,
    handoff_dir: Path,
    bundle_out_dir: Path | None = None,
    glob: str = "*.json",
    only_if_baseline_committed_in: Path | None = None,
) -> list[Path]:
    """
    SymTex-benchmark handoffs that do not yet have a **committed** asp_pipeline record
    (same contract as :mod:`asp_pipeline.run_wfm_handoff_batch` resume).

    If ``only_if_baseline_committed_in`` is set, only handoffs whose ``bundle_id`` already has
    a committed record in that directory (e.g. the original ``bundles/asp_from_wfm`` run) are
    included — for A/B re-formalization with a new ``--formalizer-prompt`` into a **separate**
    ``--bundle-out-dir`` while staying comparable to a known-good baseline.
    """
    bdir = (bundle_out_dir or (repo_root / _DEFAULT_BUNDLE_OUT)).resolve()
    base = only_if_baseline_committed_in.resolve() if only_if_baseline_committed_in is not None else None
    out: list[Path] = []
    for hp in iter_symtex_ground_truth_handoff_paths(handoff_dir, glob=glob):
        try:
            bid = load_handoff_bundle_id(hp)
        except (json.JSONDecodeError, ValueError, OSError):
            continue
        if base is not None and not is_asp_pipeline_committed(bundle_out_dir=base, bundle_id=bid):
            continue
        if is_asp_pipeline_committed(bundle_out_dir=bdir, bundle_id=bid):
            continue
        out.append(hp)
    return out
