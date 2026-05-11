"""Structural WFM handoff → minimal domain bundle files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _lines_from_handoff(data: dict[str, Any], *, pass_only: bool) -> list[str]:
    lines = data.get("lines")
    if not isinstance(lines, list):
        raise ValueError("handoff missing 'lines' array")
    out: list[str] = []
    for row in lines:
        if not isinstance(row, dict):
            continue
        nl = row.get("statement_nl")
        if not isinstance(nl, str) or not nl.strip():
            continue
        verdict = row.get("agent3_verdict")
        if pass_only and verdict is not None and str(verdict).upper() != "PASS":
            continue
        out.append(nl.strip())
    return out


def materialize_domain_bundle_from_handoff(
    *,
    handoff_path: Path,
    out_dir: Path,
    pass_only: bool = True,
    warn_stderr: bool = True,
) -> Path:
    """
    Read registry-style WFM JSON (``lines[].statement_nl``), emit ``rules.txt``
    and a **stub** ``tools.json`` (gated ``apply_refund`` only).
    Operator must still supply ``signature.py`` and ``glossary.md``.
    """
    raw = json.loads(handoff_path.read_text(encoding="utf-8"))
    nl_lines = _lines_from_handoff(raw, pass_only=pass_only)
    if not nl_lines:
        raise ValueError("no NL lines extracted from handoff")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rules.txt").write_text("\n".join(nl_lines) + "\n", encoding="utf-8")

    stub_tools = {
        "tools": [
            {
                "name": "apply_refund",
                "parameters": {},
                "is_gated": True,
            }
        ]
    }
    (out_dir / "tools.json").write_text(
        json.dumps(stub_tools, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if warn_stderr:
        print(
            "wfm_import: wrote stub tools.json. Add signature.py + glossary.md before orchestrator.",
            file=sys.stderr,
        )
    return out_dir
