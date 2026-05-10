"""Snapshot a pivot run into ``pivot_pipeline/golden_test_run`` for regression / reference."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def default_golden_dir() -> Path:
    return Path(__file__).resolve().parent / "golden_test_run"


def save_golden_snapshot(
    *,
    work_dir: Path,
    nl_source: Path,
    golden_root: Path | None = None,
    summary: dict[str, Any] | None = None,
) -> Path:
    """
    Replace ``golden_root`` contents with:
    - ``input/`` — copy of the resolved NL source file
    - ``work/`` — recursive copy of ``work_dir`` (WFM handoffs, scratches, Z3, critic, etc.)
    - ``snapshot_meta.json`` — UTC timestamp, paths, pipeline outcome (if provided)
    """
    root = (golden_root or default_golden_dir()).resolve()
    work_dir = work_dir.resolve()
    nl_source = nl_source.resolve()

    if not work_dir.is_dir():
        raise FileNotFoundError(f"work_dir is not a directory: {work_dir}")
    if not nl_source.is_file():
        raise FileNotFoundError(f"nl_source is not a file: {nl_source}")

    if root.is_dir():
        for child in root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    else:
        root.mkdir(parents=True, exist_ok=True)

    inp = root / "input"
    inp.mkdir(exist_ok=True)
    dest_in = inp / nl_source.name
    shutil.copy2(nl_source, dest_in)

    work_dst = root / "work"
    shutil.copytree(work_dir, work_dst, dirs_exist_ok=False)

    meta = {
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "work_dir": str(work_dir),
        "nl_source": str(nl_source),
        "outcome": (summary or {}).get("outcome"),
        "precheck_ok": (summary or {}).get("precheck_ok"),
    }
    (root / "snapshot_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return root
