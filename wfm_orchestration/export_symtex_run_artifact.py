"""
Emit a single human-readable document for selected SymTex batch runs: dataset NL + reference ASP,
WFM handoff and verdict timeline, and committed formalizer policy + pipeline record.

Run (from repo root)::

  python -m wfm_orchestration.export_symtex_run_artifact --bundle-prefix symtex_batch_20260423_ \\
      --out exports/symtex_batch_8_runs_artifact.md

Alternate committed formalizations (e.g. ``formalizer_new``)::

  python -m wfm_orchestration.export_symtex_run_artifact --bundle-prefix symtex_batch_20260423_ \\
      --asp-bundles-dir bundles/asp_from_wfm_formalizer_new \\
      --out exports/symtex_batch_8_runs_artifact_formalizer_new.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_REPO))

_DEFAULT_DONE = _REPO / "exports" / "wfm_symtex_batch" / "completed.jsonl"
_DEFAULT_OUT = _REPO / "exports" / "symtex_batch_8_runs_artifact.md"


def _load_done(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _find_ex(example_key: str, index: list[Any]) -> Any | None:
    if ":" not in example_key:
        return None
    t, sid = example_key.split(":", 1)
    for e in index:
        if e.task == t and e.source_id == sid:
            return e
    return None


def _handoff_narrative(h: dict[str, Any]) -> str:
    lines = h.get("lines") or []
    chrono: list[str] = []
    for ln in sorted(lines, key=lambda x: (x or {}).get("line_index", 0)):
        if not isinstance(ln, dict):
            continue
        idx = ln.get("line_index")
        v = (ln.get("agent3_verdict") or "?").strip()
        st = (ln.get("statement_nl") or "")[:200].replace("\n", " ")
        chrono.append(f"  - line {idx}  |  {v}  |  {st}")
    return "\n".join(chrono) if chrono else "  (no lines)"


def _as_md_fence(lang: str, body: str) -> str:
    b = (body or "").rstrip()
    b = b.replace("```", "`\u200b``")  # avoid breaking markdown fences
    return f"```{lang}\n{b}\n```\n"


def build_doc(
    *,
    bundle_prefix: str,
    completed_path: Path,
    repo_root: Path,
    asp_bundles_dir: Path,
) -> str:
    from wfm_orchestration.asp_demo_sources import load_symtex_paired_index

    index = load_symtex_paired_index(repo_root)
    done = _load_done(completed_path)
    picked: list[dict[str, Any]] = []
    for rec in done:
        if not rec.get("success"):
            continue
        bid = rec.get("bundle_id")
        if not isinstance(bid, str) or not bid.startswith(bundle_prefix):
            continue
        picked.append(rec)
    picked.sort(key=lambda r: (r.get("utc") or "", r.get("example_key", "")))

    try:
        asp_label = asp_bundles_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        asp_label = str(asp_bundles_dir.resolve())
    parts: list[str] = [
        "# SymTex batch runs (dataset, WFM, formalization)\n",
        f"**Generated (UTC):** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z  \n",
        f"**Filter:** `bundle_id` prefix `{bundle_prefix}`  \n",
        f"**Runs included:** {len(picked)}  \n",
        f"**Committed ASP / policy path:** `{asp_label}/` (see **Formalization** below)  \n",
        "\n",
        "Each example is in **chronological order of the WFM batch** (`completed.jsonl` `utc`). "
        "Under **WFM**, (1) batch completion time, (2) handoff path, (3) per-line `agent3_verdict` in line-index order. "
        "**Formalization** is the committed `asp_pipeline` policy `.lp` and the bundle sidecar JSON metadata. "
        "Dataset blocks use the current SymTex paired index (same as `load_symtex_paired_index`).\n",
        "\n---\n\n",
    ]

    for i, rec in enumerate(picked, 1):
        ek = rec.get("example_key", "")
        bid = rec.get("bundle_id", "")
        utc = rec.get("utc", "")
        manifest = rec.get("manifest_example_id", "")
        ta = rec.get("truth_assessment")
        ex = _find_ex(ek, index) if ek else None

        parts.append(f"## {i}. `{ek}`\n\n")
        parts.append(f"- **bundle_id:** `{bid}`\n")
        parts.append(f"- **manifest id:** `{manifest}`\n")
        parts.append(f"- **reference pair:** textual `{ex.textual_jsonl_relpath if ex else 'n/a'}`  \n")
        if ex:
            parts.append(f"  symbolic `{ex.symbolic_jsonl_relpath}`\n\n")
        else:
            parts.append("\n")

        parts.append("### Dataset: original natural language (SymTex formatted)\n\n")
        if ex:
            parts.append(_as_md_fence("text", ex.nl_document))
        else:
            parts.append("_Not found in paired index (example_key mismatch)._\n\n")

        parts.append("### Dataset: reference ASP (symbolic / paired JSONL)\n\n")
        if ex:
            parts.append(_as_md_fence("asp", ex.reference_asp_program))
        else:
            parts.append("_Missing._\n\n")

        if ex and (ex.extra or {}):
            parts.append("**Extra (SymTex row):**  \n")
            parts.append("```json\n" + json.dumps(ex.extra, indent=2, ensure_ascii=False) + "\n```\n\n")

        hp = rec.get("handoff_path")
        handoff: dict[str, Any] | None = None
        if isinstance(hp, str):
            p = Path(hp)
            if p.is_file():
                handoff = json.loads(p.read_text(encoding="utf-8"))

        if handoff is None:
            parts.append("### WFM: _(no handoff file on disk — skipped as requested)_\n\n")
        else:
            parts.append("### WFM outcomes (chronological within this run)\n\n")
            parts.append("1. **Batch completion (from `exports/wfm_symtex_batch/completed.jsonl`)**  \n")
            parts.append(f"   - `utc`: `{utc}`  \n")
            if isinstance(ta, dict):
                parts.append("   - `truth_assessment` (from that record):  \n\n")
                parts.append("```json\n" + json.dumps(ta, indent=2, ensure_ascii=False) + "\n```\n\n")
            parts.append("2. **WFM handoff**  \n")
            parts.append(f"   - file: `{Path(hp).as_posix()}`  \n")
            parts.append(
                f"   - `schema_version`: `{handoff.get('schema_version', '')}`  \n"
            )
            parts.append("3. **Line verdicts (Agent 3, order = `line_index`)**  \n\n")
            parts.append(_handoff_narrative(handoff) + "\n\n")
            uoi = handoff.get("user_original_input") or ""
            parts.append("4. **Full `user_original_input` (what WFM received — SymTex banner + per-line WFM phrasing)**  \n\n")
            parts.append(_as_md_fence("text", uoi if isinstance(uoi, str) else ""))
            hpth = Path(hp)
            logp = hpth.parent / f"{hpth.stem}.log.jsonl"
            if logp.is_file():
                parts.append(
                    f"5. **WFM run log (if present):** `{logp.as_posix()}` — see file for agent stages.  \n\n"
                )
            else:
                parts.append("5. **WFM run log:** _(none next to handoff; search `bundles/wfm_artifacts` for same stem if needed)._\n\n"
                )

        pol = asp_bundles_dir / "policies" / f"{bid}.lp"
        bjson = asp_bundles_dir / f"{bid}.json"
        if pol.is_file() and bjson.is_file():
            bdata = json.loads(bjson.read_text(encoding="utf-8"))
            parts.append("### Formalization (asp_pipeline) — committed policy\n\n")
            parts.append(
                f"- `pipeline_status`: `{bdata.get('pipeline_status')}`  \n"
            )
            parts.append(
                f"- `committed_at`: `{bdata.get('committed_at', '')}`  \n"
            )
            fp = bdata.get("formalizer_prompt")
            if isinstance(fp, str) and fp.strip():
                parts.append(f"- `formalizer_prompt` (if recorded): `{fp}`  \n")
            fps = bdata.get("formalizer_prompt_sha256")
            if isinstance(fps, str) and fps.strip():
                parts.append(f"- `formalizer_prompt_sha256`: `{fps}`  \n")
            parts.append(
                f"- `policy_model_path` (in record): `{bdata.get('policy_model_path', '')}`  \n"
            )
            parts.append(f"- `rule_ids` count: `{len(bdata.get('rule_ids') or [])}`  \n")
            plp = pol.read_text(encoding="utf-8")
            parts.append(f"- **Policy file:** `{pol.as_posix()}`\n\n")
            parts.append("**Committed `.lp` (full):**\n\n")
            parts.append(_as_md_fence("clingo", plp))
        else:
            parts.append("### Formalization: _(no committed `policies/{bundle_id}.lp` or bundle JSON — not written)_\n\n")

        parts.append("\n---\n\n")

    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle-prefix", type=str, default="symtex_batch_20260423_")
    ap.add_argument("--from-completed", type=Path, default=_DEFAULT_DONE)
    ap.add_argument(
        "--asp-bundles-dir",
        type=Path,
        default=_REPO / "bundles" / "asp_from_wfm",
        help="Directory with per-bundle .json, policies/<bundle_id>.lp (default: bundles/asp_from_wfm).",
    )
    ap.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    args = ap.parse_args()
    text = build_doc(
        bundle_prefix=args.bundle_prefix,
        completed_path=args.from_completed,
        repo_root=_REPO,
        asp_bundles_dir=(args.asp_bundles_dir if args.asp_bundles_dir.is_absolute() else _REPO / args.asp_bundles_dir).resolve(),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
