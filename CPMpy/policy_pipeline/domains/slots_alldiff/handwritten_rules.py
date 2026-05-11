"""Reference rule for slots_alldiff (AllDifferent = Pattern B)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import cpmpy as cp

_dir = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("slots_sig", _dir / "signature.py")
if _spec is None or _spec.loader is None:
    raise ImportError("signature")
_sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sig)

rule_1 = cp.AllDifferent([_sig.slot_a, _sig.slot_b, _sig.slot_c])


def all_rules() -> dict[str, object]:
    return {"rule_1": rule_1}
