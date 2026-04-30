"""Resolve SMT-LIB policy text for Z3 checks (bundled default or WFM pipeline output path)."""

from __future__ import annotations

from pathlib import Path

from agentsim.runtime.snapshot import policy_v0_text


def load_policy_smt2_file(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def resolve_guardrails_refined_policy_path() -> Path:
    """Path to ``policy_model_refined.smt2`` (repo export)."""

    return (
        Path(__file__).resolve().parents[2]
        / "exports"
        / "nl_chunk_smt_runs"
        / "04_agentic_guardrails"
        / "policy_model_refined.smt2"
    )


def resolve_guardrails_policy_text(
    *,
    policy_smt2_path: Path | str | None = None,
) -> str:
    """Load refined guardrails policy text (default: export path)."""

    p = Path(policy_smt2_path) if policy_smt2_path is not None else resolve_guardrails_refined_policy_path()
    return p.read_text(encoding="utf-8")


def resolve_z3_policy_text(
    *,
    policy_smt2_path: Path | str | None,
    policy_smt2_text: str | None,
) -> str:
    """
    Policy text for :class:`~agentsim.runtime.z3_legality.Z3LegalityChecker`.

    Precedence: explicit file → inline string → bundled ``policy_v0.smt2``.
    """
    if policy_smt2_path is not None and policy_smt2_text is not None:
        msg = "pass at most one of policy_smt2_path, policy_smt2_text"
        raise ValueError(msg)
    if policy_smt2_path is not None:
        return load_policy_smt2_file(policy_smt2_path)
    if policy_smt2_text is not None:
        return policy_smt2_text
    return policy_v0_text()
