from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# NagV repo root: parent of ``pivot_pipeline/`` (contains ``nagv/``, ``pivot_pipeline/``, …).
_NAGV_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_v1_policy_encodability_contract() -> str:
    """Shared IR limits for extractor, WFM pivot agents, and chunk/ABORT scope rewrites."""
    p = PROMPTS_DIR / "v1_policy_encodability_contract.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing v1 encodability contract: {p}")
    return p.read_text(encoding="utf-8")


def read_extractor_vnext_addendum() -> str:
    """Optional expansion templates for Phase 1 extract (appended after encodability contract)."""
    p = PROMPTS_DIR / "extractor_vnext_addendum.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing extractor vNext addendum: {p}")
    return p.read_text(encoding="utf-8")


def read_vnext_template_examples() -> str:
    """Minimal JSON examples per vNext template (repairer / extract reference)."""
    p = PROMPTS_DIR / "vnext_template_examples.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing vNext template examples: {p}")
    return p.read_text(encoding="utf-8")


def read_repairer_ir_normative() -> str:
    """Shared denylist, allowlists, and v1 IR shape for repairer and test-repairer."""
    p = PROMPTS_DIR / "repairer_ir_normative.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing repairer IR normative block: {p}")
    return p.read_text(encoding="utf-8")


def read_test_repairer_ir_addendum() -> str:
    p = PROMPTS_DIR / "test_repairer_ir_addendum.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing test-repairer IR addendum: {p}")
    return p.read_text(encoding="utf-8")


def read_cross_repairer_ir_addendum() -> str:
    p = PROMPTS_DIR / "cross_repairer_ir_addendum.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing cross-repairer IR addendum: {p}")
    return p.read_text(encoding="utf-8")


def read_semantic_repairer_ir_addendum() -> str:
    p = PROMPTS_DIR / "semantic_repairer_ir_addendum.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing semantic-repairer IR addendum: {p}")
    return p.read_text(encoding="utf-8")


def read_temporal_surrogates_addendum() -> str:
    """Eight temporal surrogate patterns (T1–T8); no new template_class values."""
    p = PROMPTS_DIR / "temporal_surrogates_addendum.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing temporal surrogates addendum: {p}")
    return p.read_text(encoding="utf-8")


def read_temporal_surrogates_examples() -> str:
    """NL examples per temporal pattern (optional second inject)."""
    p = PROMPTS_DIR / "temporal_surrogates_examples.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing temporal surrogates examples: {p}")
    return p.read_text(encoding="utf-8")


def read_subjective_assessment_surrogates_addendum() -> str:
    """Qualitative norms as bool surrogates; forbid invented proficiency metrics."""
    p = PROMPTS_DIR / "subjective_assessment_surrogates.md"
    if not p.is_file():
        raise FileNotFoundError(f"missing subjective assessment surrogates addendum: {p}")
    return p.read_text(encoding="utf-8")


def read_pivot_encodability_prompt_stack() -> str:
    """Shared contract + vNext + temporal + subjective assessment addenda (inject into agents)."""
    return (
        read_v1_policy_encodability_contract()
        + "\n\n---\n\n"
        + read_extractor_vnext_addendum()
        + "\n\n---\n\n"
        + read_temporal_surrogates_addendum()
        + "\n\n---\n\n"
        + read_subjective_assessment_surrogates_addendum()
    )


def resolve_existing_user_file(
    path: Path,
    *,
    cwd: Path | None = None,
    nagv_project_root: Path | None = None,
) -> Path:
    """
    Resolve a relative user path to an existing file.

    On Windows, paths are case-insensitive. Running from the NagV project directory with
    ``--input NagV/pivot_pipeline/...`` incorrectly resolves the first segment to the
    ``nagv`` *package* directory (same spelling, different folder). This helper retries
    by stripping a leading ``nagv`` segment and by resolving relative to the NagV
    project root.
    """
    cwd = cwd.resolve() if cwd is not None else Path.cwd().resolve()
    root = nagv_project_root.resolve() if nagv_project_root is not None else _NAGV_PROJECT_ROOT

    if path.is_absolute():
        return path.resolve()

    rel = path.as_posix().lstrip("./")
    parts = tuple(Path(rel).parts)
    candidates: list[Path] = []

    def add(p: Path) -> None:
        candidates.append(p.resolve())

    add(cwd / path)
    add(root / path)
    if parts and parts[0].casefold() == "nagv" and len(parts) > 1:
        tail = Path(*parts[1:])
        add(cwd / tail)
        add(root / tail)

    seen: set[Path] = set()
    for c in candidates:
        if c in seen:
            continue
        seen.add(c)
        if c.is_file():
            return c
    return (cwd / path).resolve()
