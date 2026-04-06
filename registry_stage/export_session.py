"""Dev-only session export (not a production registry.json commit)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from registry_stage.models import DevSessionSnapshot


def export_session(path: str | Path, snapshot: DevSessionSnapshot, **json_dumps_kw: Any) -> None:
    """
    Write `snapshot` as JSON. Top-level metadata includes `dev_export: true` via
    `DevSessionSnapshot.to_jsonable()`.
    """
    p = Path(path)
    payload = snapshot.to_jsonable()
    kwargs = {"indent": 2, "ensure_ascii": False}
    kwargs.update(json_dumps_kw)
    p.write_text(json.dumps(payload, **kwargs) + "\n", encoding="utf-8")
