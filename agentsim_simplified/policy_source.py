"""Resolve path to ``policy_model_refined_simpl.smt2``."""

from __future__ import annotations

from pathlib import Path


def repo_root_from_here() -> Path:
    """``agentsim_simplified/`` -> workspace root."""

    return Path(__file__).resolve().parents[1]


def default_refined_policy_path() -> Path:
    return (
        repo_root_from_here()
        / "exports"
        / "nl_chunk_smt_runs"
        / "agentsim_simplified"
        / "policy_model_refined_simpl.smt2"
    )
