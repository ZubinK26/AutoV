"""
Persist WFM ``HandoffBundle`` JSON for ``smt_pipeline`` and append a machine-readable manifest.

Layout (under repo root by default)::

    bundles/wfm_artifacts/
      <bundle_id>.json          # registry_persistence_v1 handoff (SMT input)
      manifest.jsonl            # one JSON object per successful write
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DEFAULT_REL = Path("bundles") / "wfm_artifacts"


def default_handoff_dir(repo_root: Path) -> Path:
    return (repo_root / _DEFAULT_REL).resolve()


def ensure_handoff_dir(repo_root: Path) -> Path:
    d = default_handoff_dir(repo_root)
    d.mkdir(parents=True, exist_ok=True)
    return d


def hard_batch_bundle_prefix(ex_id: str) -> str:
    """``bundle_id_prefix`` used by ``run_hard_batch`` (hyphens in ``ex_id`` become underscores)."""
    return f"hard_{ex_id.replace('-', '_')}"


def list_existing_handoffs_for_batch_example(repo_root: Path, ex_id: str) -> list[Path]:
    """
    List handoff JSON files already written for a batch example, e.g. ``hard_F_8_<stamp>_<hex>.json``.

    Sorted by path name (UTC stamps in the id sort lexicographically by time).
    """
    d = ensure_handoff_dir(repo_root)
    prefix = hard_batch_bundle_prefix(ex_id)
    return sorted(d.glob(f"{prefix}_*.json"))


def handoff_write_path(
    repo_root: Path,
    bundle_id: str,
    *,
    handoff_dir: Path | None = None,
) -> Path:
    """Stable filename: ``<handoff_dir>/<bundle_id>.json`` (sanitized)."""
    d = handoff_dir if handoff_dir is not None else ensure_handoff_dir(repo_root)
    d.mkdir(parents=True, exist_ok=True)
    safe = bundle_id.replace("/", "_").replace("\\", "_")
    return d / f"{safe}.json"


def manifest_path(repo_root: Path) -> Path:
    return ensure_handoff_dir(repo_root) / "manifest.jsonl"


def record_handoff_artifact(
    repo_root: Path,
    *,
    bundle_id: str,
    example_id: str | None,
    handoff_path: Path,
    skip_registry: bool,
) -> None:
    """Append one line to ``manifest.jsonl`` for audit and SMT pipeline discovery."""
    mp = manifest_path(repo_root)
    try:
        rel_s = str(handoff_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        rel_s = str(handoff_path.resolve())
    rec: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "bundle_id": bundle_id,
        "example_id": example_id,
        "handoff_relative_path": rel_s,
        "skip_registry": skip_registry,
        "smt_pipeline_hint": f"python -m smt_pipeline --handoff {rel_s}",
    }
    with mp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
