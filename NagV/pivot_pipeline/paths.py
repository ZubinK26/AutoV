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
