"""Hand-written reference policy (vector + global)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import cpmpy as cp

_dir = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("inv_sig", _dir / "signature.py")
if _spec is None or _spec.loader is None:
    raise ImportError("signature")
_sig = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sig)

rule_1 = cp.all(_sig.bin_counts[i] <= 4 for i in range(_sig.N_BINS))


def all_rules() -> dict[str, object]:
    return {"rule_1": rule_1}
