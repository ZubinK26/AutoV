"""Reference types for Z3 formalization (optional import from generated candidates).

Candidates may return a plain ``dict`` instead; this module documents the contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Z3CheckResult:
    """Return value contract for ``run_z3_check()``."""

    status: str  # "sat" | "unsat" | "unknown"
    unsat_core: list[str] | None = None
    model_excerpt: str | None = None
    diagnostics: str | None = None

    def as_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"status": self.status}
        if self.unsat_core is not None:
            d["unsat_core"] = self.unsat_core
        if self.model_excerpt is not None:
            d["model_excerpt"] = self.model_excerpt
        if self.diagnostics is not None:
            d["diagnostics"] = self.diagnostics
        return d

