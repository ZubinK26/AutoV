from __future__ import annotations

import sqlite3
from importlib import resources

from agentsim.runtime.snapshot_full import full_snapshot_builder, full_snapshot_for_call

__all__ = [
    "default_snapshot_builder",
    "full_snapshot_builder",
    "full_snapshot_for_call",
    "policy_v0_text",
]


def default_snapshot_builder(
    conn: sqlite3.Connection,
    *,
    interaction_id: str,
):
    """Alias for :func:`full_snapshot_builder` (all write tools manifest-backed)."""

    return full_snapshot_builder(conn, interaction_id=interaction_id)


def policy_v0_text() -> str:
    """Bundled SMT-LIB policy (Slice C)."""

    with resources.files("agentsim.runtime.data").joinpath("policy_v0.smt2").open(
        "r",
        encoding="utf-8",
    ) as f:
        return f.read()
