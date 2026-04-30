from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FabricationReport:
    ok: bool
    issues: list[str]


def fabrication_check_stub(
    _final_customer_message: str,
    *,
    _interaction_id: str,
) -> FabricationReport:
    """v2 hook (agentsim/02): stub always passes."""

    return FabricationReport(ok=True, issues=[])
