"""Remove generated Phase 0 / orchestrator outputs so a domain or bundle dir can be rerun cleanly."""

from __future__ import annotations

import shutil
from pathlib import Path

# Paths relative to domain_dir created by Phase 0 or left from prior attempts.
_PHASE0_RELATIVE_FILES = (
    "signature.py",
    "glossary.md",
    "signature_rationale.json",
    "refiner_decisions.json",
    "signature_check_report.json",
    "workflow_state.json",
    "signature_draft_log.jsonl",
    "glossary_draft_log.jsonl",
)


def reset_phase0_artifacts(domain_dir: Path) -> list[str]:
    """Delete known Phase 0 artifacts under *domain_dir*. Returns removed paths (POSIX strings)."""
    d = Path(domain_dir).resolve()
    removed: list[str] = []
    for name in _PHASE0_RELATIVE_FILES:
        p = d / name
        if p.is_file():
            p.unlink()
            removed.append(p.as_posix())
    for p in d.glob("human_review_*.json"):
        if p.is_file():
            p.unlink()
            removed.append(p.as_posix())
    return removed


def reset_orchestrator_out_dir(out_dir: Path) -> bool:
    """
    Delete *out_dir* entirely if it exists, then recreate an empty directory.
    Returns True if something was removed or the directory was created.
    """
    o = Path(out_dir).resolve()
    existed = o.exists()
    if o.is_dir():
        shutil.rmtree(o)
    elif o.is_file():
        o.unlink()
    o.mkdir(parents=True, exist_ok=True)
    return existed


def reset_domain_for_rerun(
    domain_dir: Path,
    *,
    out_dir: Path | None = None,
) -> dict[str, object]:
    """Reset Phase 0 files under *domain_dir* and optionally wipe *out_dir*."""
    phase0_removed = reset_phase0_artifacts(domain_dir)
    out_reset = False
    if out_dir is not None:
        out_reset = reset_orchestrator_out_dir(out_dir)
    return {
        "domain_dir": str(Path(domain_dir).resolve()),
        "phase0_removed": phase0_removed,
        "out_dir_reset": str(Path(out_dir).resolve()) if out_dir is not None else None,
        "out_dir_had_content": out_reset,
    }
