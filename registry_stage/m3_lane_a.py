"""
Lane A — live Gemini M3 matrix → JSONL under ``eval_runs/``.

See ``development_plan_registry_stage_v1.md`` M3 Lane A and ``REGISTRY_M3_EVAL_DECISIONS.md``.

**Default matrix (unchanged):** both ``query_mode`` values × all three ``masking_preset`` values (6 configs × N lines).

**Optional narrowing** (same module — full 2×3 remains the default when flags are omitted):

- ``--query-modes`` — subset of ``multi_query_fuse`` / ``single_concat``.
- ``--masking-presets`` — subset of ``standard`` / ``aggressive`` / ``conservative``.
- ``--authoritative-min-score`` — forwarded to ``LineDriverConfig`` (override session default).

Examples (repo root, ``GEMINI_API_KEY`` set)::

    # Classic full 2×3 matrix on business fixtures
    python -m registry_stage.m3_lane_a --out registry_stage/eval_runs/eval_try.jsonl

    # Protocol A — query-mode comparison, conservative masking only (2 × N API calls)
    python -m registry_stage.m3_lane_a \\
        --registry registry_stage/eval_fixtures/m3_retrieval_eval_registry.json \\
        --lines registry_stage/eval_fixtures/m3_retrieval_eval_lines.json \\
        --masking-presets conservative \\
        --label query_mode_conservative \\
        --out registry_stage/eval_runs/eval_query_mode.jsonl

    # Protocol B — prefer the sweep helper (single_concat + conservative, one JSONL per score):
    python -m registry_stage.m3_protocol_b_minscore \\
        --scores 0.18 0.22 0.28 0.32 0.35 \\
        --out-dir registry_stage/eval_runs

    # Or a single min-score run explicitly:
    python -m registry_stage.m3_lane_a \\
        --registry registry_stage/eval_fixtures/m3_retrieval_eval_registry.json \\
        --lines registry_stage/eval_fixtures/m3_retrieval_eval_lines.json \\
        --query-modes single_concat \\
        --masking-presets conservative \\
        --authoritative-min-score 0.22 \\
        --label protocol_b_once \\
        --out registry_stage/eval_runs/eval_protocol_b_once.jsonl

Score Protocol A/B JSONL (no API)::

    python -m registry_stage.m3_eval_score \\
        --jsonl registry_stage/eval_runs/eval_query_mode.jsonl \\
        --labels registry_stage/eval_fixtures/m3_retrieval_eval_labels.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence, cast

from registry_stage.line_driver import LineDriverConfig, run_search_and_gaps_for_line
from registry_stage.llm.agents import PROMPTS_DIR
from registry_stage.loaders import load_registry
from registry_stage.models import StructuredGap
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex

QueryModeLit = Literal["multi_query_fuse", "single_concat"]
MaskingLit = Literal["standard", "aggressive", "conservative"]


def resolve_lane_a_matrix_axes(
    query_modes: Sequence[str] | None,
    masking_presets: Sequence[str] | None,
) -> tuple[list[QueryModeLit], list[MaskingLit]]:
    """
    Expand CLI selections into lists. ``None`` for an argument means “use full default matrix”
    (both query modes; all three masking presets).
    """
    default_q: list[QueryModeLit] = ["multi_query_fuse", "single_concat"]
    default_m: list[MaskingLit] = ["standard", "aggressive", "conservative"]
    q = list(query_modes) if query_modes is not None else default_q
    m = list(masking_presets) if masking_presets is not None else default_m
    if not q:
        raise ValueError("lane_a: query_modes must be non-empty")
    if not m:
        raise ValueError("lane_a: masking_presets must be non-empty")
    return cast(list[QueryModeLit], q), cast(list[MaskingLit], m)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_head_short() -> str | None:
    try:
        root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if root.returncode != 0:
            return None
        rev = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            cwd=root.stdout.strip(),
        )
        if rev.returncode != 0:
            return None
        return rev.stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def _gap_to_json(g: StructuredGap) -> dict[str, Any]:
    d = asdict(g)
    d["domain_hints"] = list(d["domain_hints"])
    return d


def _result_row(
    *,
    example_id: str,
    line_index: int,
    query_mode: QueryModeLit,
    masking_preset: MaskingLit,
    res: Any,
) -> dict[str, Any]:
    def hits_json(hits: tuple) -> list[dict[str, Any]]:
        return [{"entry_id": h.entry_id, "score": float(h.score)} for h in hits]

    sq = list(res.search_queries_used)
    sq_short = [s[:400] + ("…" if len(s) > 400 else "") for s in sq]
    return {
        "row_kind": "result",
        "example_id": example_id,
        "line_index": line_index,
        "query_mode": query_mode,
        "masking_preset": masking_preset,
        "statement_nl": res.statement_nl,
        "semantic_backend_label": res.semantic_backend_label,
        "authoritative_min_score": res.authoritative_min_score,
        "hits": hits_json(res.hits),
        "authoritative_hits": hits_json(res.authoritative_hits),
        "raw_expansion_phrases": list(res.raw_expansion_phrases),
        "expansion_phrases": list(res.expansion_phrases),
        "raw_structured_gaps": [_gap_to_json(g) for g in res.raw_structured_gaps],
        "structured_gaps": [_gap_to_json(g) for g in res.structured_gaps],
        "gap_spans": list(res.gap_spans),
        "search_queries_used": sq_short,
        "single_concat_query_truncated": res.single_concat_query_truncated,
    }


def default_fixture_dir() -> Path:
    return Path(__file__).resolve().parent / "eval_fixtures"


def run_matrix(
    *,
    registry_path: Path,
    lines_path: Path,
    out_path: Path,
    index_mode: str,
    eval_label: str,
    query_modes: Sequence[str] | None = None,
    masking_presets: Sequence[str] | None = None,
    authoritative_min_score: float | None = None,
) -> None:
    modes, masks = resolve_lane_a_matrix_axes(query_modes, masking_presets)
    reg = load_registry(registry_path)
    lines_payload = json.loads(lines_path.read_text(encoding="utf-8"))
    raw_lines = lines_payload.get("lines")
    if not isinstance(raw_lines, list):
        raise ValueError("lines JSON must contain a 'lines' array")

    if index_mode == "stub":
        session = RegistrySession.from_entries(
            reg.entries,
            semantic_index=StubKeywordSemanticIndex(),
            index_preference="stub",
        )
    else:
        session = RegistrySession.from_entries(reg.entries, index_preference="faiss")

    expand_md = PROMPTS_DIR / "registry_search_expand.md"
    gap_md = PROMPTS_DIR / "registry_gap_extract.md"
    header: dict[str, Any] = {
        "row_kind": "header",
        "eval_protocol_version": "m3_lane_a_v1",
        "eval_label": eval_label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "gemini_model": os.environ.get("GEMINI_MODEL", ""),
        "registry_path": str(registry_path.as_posix()),
        "lines_path": str(lines_path.as_posix()),
        "index_mode": index_mode,
        "matrix_selection": {
            "query_modes": list(modes),
            "masking_presets": list(masks),
            "authoritative_min_score": authoritative_min_score,
        },
        "prompt_sha256": {
            "registry_search_expand.md": _sha256_file(expand_md),
            "registry_gap_extract.md": _sha256_file(gap_md),
        },
        "git_commit_short": _git_head_short(),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        fp.write(json.dumps(header, ensure_ascii=False) + "\n")
        for qm in modes:
            for mp in masks:
                for item in raw_lines:
                    if not isinstance(item, dict):
                        continue
                    st = item.get("statement_nl")
                    if not isinstance(st, str) or not st.strip():
                        continue
                    eid = str(item.get("id", "")) or f"line_{item.get('line_index', 0)}"
                    li = int(item.get("line_index", 0)) if isinstance(item.get("line_index"), int) else 0
                    cfg = LineDriverConfig(
                        enable_llm=True,
                        query_mode=qm,
                        masking_preset=mp,
                        authoritative_min_score=authoritative_min_score,
                    )
                    res = run_search_and_gaps_for_line(session, li, st.strip(), config=cfg)
                    row = _result_row(
                        example_id=eid,
                        line_index=li,
                        query_mode=qm,
                        masking_preset=mp,
                        res=res,
                    )
                    fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="M3 Lane A matrix → JSONL (live Gemini).")
    fd = default_fixture_dir()
    parser.add_argument(
        "--registry",
        type=Path,
        default=fd / "m3_business_registry.json",
        help="registry JSON (default: eval_fixtures/m3_business_registry.json)",
    )
    parser.add_argument(
        "--lines",
        type=Path,
        default=fd / "m3_business_lines.json",
        help="lines JSON (default: eval_fixtures/m3_business_lines.json)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="output JSONL path (e.g. registry_stage/eval_runs/eval_20260405.jsonl)",
    )
    parser.add_argument(
        "--index",
        choices=("faiss", "stub"),
        default="faiss",
        help="semantic index backend (default faiss; stub for fast local keyword runs)",
    )
    parser.add_argument(
        "--label",
        default="lane_a",
        help="short label included in JSONL header",
    )
    parser.add_argument(
        "--query-modes",
        nargs="+",
        choices=("multi_query_fuse", "single_concat"),
        default=None,
        metavar="MODE",
        help="subset of query modes (default: both). Example: --query-modes multi_query_fuse",
    )
    parser.add_argument(
        "--masking-presets",
        nargs="+",
        choices=("standard", "aggressive", "conservative"),
        default=None,
        metavar="PRESET",
        help="subset of masking presets (default: all three). Example: --masking-presets conservative",
    )
    parser.add_argument(
        "--authoritative-min-score",
        type=float,
        default=None,
        help="override session default authoritative hit cutoff (min-score sweep)",
    )
    args = parser.parse_args()
    run_matrix(
        registry_path=args.registry,
        lines_path=args.lines,
        out_path=args.out,
        index_mode=args.index,
        eval_label=args.label,
        query_modes=args.query_modes,
        masking_presets=args.masking_presets,
        authoritative_min_score=args.authoritative_min_score,
    )


if __name__ == "__main__":
    main()
