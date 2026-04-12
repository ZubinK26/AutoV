"""
G9 — **warm-registry two-run** (stakeholder / process guard).

Runs **`registry_stage.run`** twice:

1. **Seed** — handoff bundle A on an empty session, then **`--save-registry`** to a JSON path.
2. **Reuse** — handoff bundle B with **`--registry`** set to that path so search/resolve see prior entries.

Same flags as **`run`**: **`GEMINI_API_KEY`** for M4 resolve (and M3 unless **`--no-llm`**). Prefer **`--index faiss`** for realistic retrieval; **`--index stub`** for quick wiring checks.

Example (from repo root)::

  python -m registry_stage.warm_registry_two_run \\
      --registry-out exports/warm_after_seed.json \\
      --export-seed exports/dev_session_seed.json \\
      --export-reuse exports/dev_session_reuse.json

Defaults use **`eval_fixtures/m4_warm_seed_bundle.json`** and **`m4_warm_reuse_bundle.json`**
(aligned with **`m4_warm_eval`**). See **`development_plan_wfm_registry_e2e_demo.md`** (G9).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence

_REPO = Path(__file__).resolve().parent.parent

_DEFAULT_SEED = _REPO / "registry_stage" / "eval_fixtures" / "m4_warm_seed_bundle.json"
_DEFAULT_REUSE = _REPO / "registry_stage" / "eval_fixtures" / "m4_warm_reuse_bundle.json"
_DEFAULT_REGISTRY_OUT = _REPO / "exports" / "warm_after_seed_registry.json"


def run_warm_two_phase(
    *,
    seed_bundle: Path,
    reuse_bundle: Path,
    registry_out: Path,
    index: str = "faiss",
    no_llm: bool = False,
    export_seed: Path | None = None,
    export_reuse: Path | None = None,
    run_main: Callable[[list[str] | None], int] | None = None,
) -> int:
    """
    Execute seed run then reuse run. ``run_main`` defaults to ``registry_stage.run.main``;
    injected for tests.
    """
    if run_main is None:
        from registry_stage.run import main as run_main

    seed_args: list[str] = [
        "--bundle",
        str(seed_bundle),
        "--save-registry",
        str(registry_out),
        "--index",
        index,
    ]
    if no_llm:
        seed_args.append("--no-llm")
    if export_seed is not None:
        seed_args.extend(["--export", str(export_seed)])

    print("[G9 warm 1/2] Seed bundle → save registry", file=sys.stderr)
    rc = run_main(seed_args)
    if rc != 0:
        print(f"[G9 warm 1/2] failed with exit {rc}", file=sys.stderr)
        return rc

    reuse_args: list[str] = [
        "--bundle",
        str(reuse_bundle),
        "--registry",
        str(registry_out),
        "--index",
        index,
    ]
    if no_llm:
        reuse_args.append("--no-llm")
    if export_reuse is not None:
        reuse_args.extend(["--export", str(export_reuse)])

    print("[G9 warm 2/2] Reuse bundle → warm registry", file=sys.stderr)
    rc = run_main(reuse_args)
    if rc != 0:
        print(f"[G9 warm 2/2] failed with exit {rc}", file=sys.stderr)
    return rc


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="G9 — run registry_stage twice: seed bundle + save-registry, then reuse bundle + --registry."
    )
    p.add_argument(
        "--seed-bundle",
        type=Path,
        default=_DEFAULT_SEED,
        help=f"First handoff JSON (default: {_DEFAULT_SEED.name})",
    )
    p.add_argument(
        "--reuse-bundle",
        type=Path,
        default=_DEFAULT_REUSE,
        help=f"Second handoff JSON (default: {_DEFAULT_REUSE.name})",
    )
    p.add_argument(
        "--registry-out",
        type=Path,
        default=_DEFAULT_REGISTRY_OUT,
        help=f"Written after run 1; loaded in run 2 (default: under repo exports/)",
    )
    p.add_argument(
        "--export-seed",
        type=Path,
        default=None,
        help="Optional dev session JSON path for run 1 (--export).",
    )
    p.add_argument(
        "--export-reuse",
        type=Path,
        default=None,
        help="Optional dev session JSON path for run 2 (--export).",
    )
    p.add_argument("--index", choices=("stub", "faiss"), default="faiss", help="Semantic index backend.")
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable M3 Gemini (M4 resolve still uses Gemini).",
    )
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    for label, path in ("--seed-bundle", args.seed_bundle), ("--reuse-bundle", args.reuse_bundle):
        if not path.is_file():
            print(f"error: {label} not found: {path}", file=sys.stderr)
            return 2

    args.registry_out.parent.mkdir(parents=True, exist_ok=True)
    if args.export_seed is not None:
        args.export_seed.parent.mkdir(parents=True, exist_ok=True)
    if args.export_reuse is not None:
        args.export_reuse.parent.mkdir(parents=True, exist_ok=True)

    return run_warm_two_phase(
        seed_bundle=args.seed_bundle.resolve(),
        reuse_bundle=args.reuse_bundle.resolve(),
        registry_out=args.registry_out.resolve(),
        index=args.index,
        no_llm=args.no_llm,
        export_seed=args.export_seed,
        export_reuse=args.export_reuse,
    )


if __name__ == "__main__":
    raise SystemExit(main())
