"""Tests for OUT_OF_SCOPE parsing / pivot OOS rewrite assist."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from wfm_orchestration.oos_rewrite_suggest import parse_out_of_scope_entries


def test_parse_out_of_scope_entries() -> None:
    a3 = """PASS: 1. "A."
OUT_OF_SCOPE: 2. "B." | temporal ordering
OUT_OF_SCOPE: 3. "C." | vague
PASS: 4. "D."
"""
    oos = parse_out_of_scope_entries(a3)
    assert oos == [(2, "B.", "temporal ordering"), (3, "C.", "vague")]
