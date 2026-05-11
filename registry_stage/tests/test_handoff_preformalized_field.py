"""Optional ``preformalized_logic`` on handoff lines (SMT preformalizer)."""

from __future__ import annotations

import json
from pathlib import Path

from registry_stage.loaders import load_handoff_bundle, parse_handoff_bundle
from registry_stage.models import SCHEMA_VERSION, HandoffBundle, HandoffLine, handoff_bundle_to_dict


def test_parse_handoff_with_preformalized_logic() -> None:
    raw = {
        "schema_version": SCHEMA_VERSION,
        "bundle_id": "b1",
        "user_original_input": "u",
        "lines": [
            {
                "line_index": 0,
                "statement_nl": "Every cat is a mammal.",
                "agent3_verdict": "PASS",
                "preformalized_logic": "For all x, if Cat(x) then Mammal(x).",
            },
        ],
    }
    b = parse_handoff_bundle(raw)
    assert b.lines[0].preformalized_logic == "For all x, if Cat(x) then Mammal(x)."


def test_roundtrip_preformalized_via_dict(tmp_path: Path) -> None:
    b = HandoffBundle(
        schema_version=SCHEMA_VERSION,
        bundle_id="b2",
        user_original_input="u",
        lines=[
            HandoffLine(0, "R.", "PASS", preformalized_logic="abstract R"),
        ],
    )
    p = tmp_path / "h.json"
    p.write_text(json.dumps(handoff_bundle_to_dict(b), indent=2), encoding="utf-8")
    b2 = load_handoff_bundle(p)
    assert b2.lines[0].preformalized_logic == "abstract R"
