"""
Stable IDs and timestamps for WFM → registry handoff (**e2e plan G3–G5**).

See ``development_plan_wfm_registry_e2e_demo.md``. All times are **UTC**.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone


def utc_now_iso_z() -> str:
    """ISO-8601 UTC with ``Z`` suffix (audit-friendly)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_bundle_id(*, prefix: str = "demo") -> str:
    """
    Unique bundle id for one acceptance / handoff.

    Format: ``{prefix}_<YYYYMMDD>_<HHMMSS>Z_<8hex>`` — human-sortable, collision-resistant.
    """
    p = prefix.strip() or "demo"
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]{0,31}$", p):
        raise ValueError(
            "bundle_id prefix must match ^[a-zA-Z][a-zA-Z0-9_-]{0,31}$ "
            f"(got {p!r})"
        )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    return f"{p}_{stamp}_{uuid.uuid4().hex[:8]}"


def orchestration_run_id_accept(*, bundle_id: str, outer_pass_index: int) -> str:
    """
    Correlates logs / JSONL to this accept event (**G5**).

    Tied to ``bundle_id`` and WFM outer-pass index (0-based).
    """
    safe = bundle_id.replace("/", "_").replace("\\", "_")[:120]
    return f"orr_{safe}_p{outer_pass_index}_accept"


def wfm_pipeline_timestamps_at_accept(*, confirmation_accepted_utc: str | None = None) -> dict[str, str]:
    """
    Minimal audit object for handoff (**G4**).

    ``confirmation_accepted_utc`` defaults to **now** if omitted.
    """
    ts = confirmation_accepted_utc or utc_now_iso_z()
    return {"confirmation_accepted_utc": ts}
