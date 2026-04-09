"""
Protocol B — sweep ``authoritative_min_score`` (live Gemini).

Uses **locked defaults from Protocol A** (see ``REGISTRY_M3_EVAL_DECISIONS.md``):

- ``query_mode``: ``single_concat`` only
- ``masking_preset``: ``conservative`` only

For each score in ``--scores``, writes one JSONL (N lines per file). **No API** for grading:
run ``m3_eval_score`` on each output with ``m3_retrieval_eval_labels.json`` and pick the
largest score where all required ``entry_id``s still appear in ``authoritative_hits``.

**Example** (repo root, ``GEMINI_API_KEY`` set)::

    python -m registry_stage.m3_protocol_b_minscore \\
        --scores 0.18 0.22 0.28 0.324 0.35 0.40 \\
        --out-dir registry_stage/eval_runs

**Grade** (after each file exists)::

    python -m registry_stage.m3_eval_score \\
        --jsonl registry_stage/eval_runs/eval_protocol_b_minscore_0p280.jsonl \\
        --labels registry_stage/eval_fixtures/m3_retrieval_eval_labels.json

To run a **single** score without this helper, use ``m3_lane_a`` with the same flags::

    python -m registry_stage.m3_lane_a \\
        --registry registry_stage/eval_fixtures/m3_retrieval_eval_registry.json \\
        --lines registry_stage/eval_fixtures/m3_retrieval_eval_lines.json \\
        --query-modes single_concat \\
        --masking-presets conservative \\
        --authoritative-min-score 0.35 \\
        --label protocol_b_once \\
        --out registry_stage/eval_runs/eval_protocol_b_once.jsonl
"""

from __future__ import annotations

import argparse
from pathlib import Path

from registry_stage.m3_lane_a import default_fixture_dir, run_matrix


def score_tag_for_filename(score: float) -> str:
    """Stable filename fragment, e.g. ``0.28`` → ``0p280``."""
    return f"{score:.3f}".replace(".", "p")


def main() -> None:
    fd = default_fixture_dir()
    parser = argparse.ArgumentParser(
        description=(
            "Protocol B: sweep authoritative_min_score with single_concat + conservative "
            "(retrieval eval fixtures by default)."
        )
    )
    parser.add_argument(
        "--scores",
        nargs="+",
        type=float,
        required=True,
        metavar="SCORE",
        help="Cutoffs to try, e.g. 0.18 0.22 0.28 0.35 — one JSONL per value",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("registry_stage/eval_runs"),
        help="Output directory (default: registry_stage/eval_runs)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=fd / "m3_retrieval_eval_registry.json",
        help="Registry JSON (default: m3_retrieval_eval_registry.json)",
    )
    parser.add_argument(
        "--lines",
        type=Path,
        default=fd / "m3_retrieval_eval_lines.json",
        help="Lines JSON (default: m3_retrieval_eval_lines.json)",
    )
    parser.add_argument(
        "--index",
        choices=("faiss", "stub"),
        default="faiss",
        help="Semantic index backend (default: faiss)",
    )
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for score in args.scores:
        tag = score_tag_for_filename(score)
        out_path = args.out_dir / f"eval_protocol_b_minscore_{tag}.jsonl"
        run_matrix(
            registry_path=args.registry,
            lines_path=args.lines,
            out_path=out_path,
            index_mode=args.index,
            eval_label=f"protocol_b_minscore_{score:g}",
            query_modes=["single_concat"],
            masking_presets=["conservative"],
            authoritative_min_score=score,
        )
        written.append(out_path)

    print("Protocol B sweep finished (single_concat + conservative).")
    for p in written:
        print(f"  {p.as_posix()}")


if __name__ == "__main__":
    main()
