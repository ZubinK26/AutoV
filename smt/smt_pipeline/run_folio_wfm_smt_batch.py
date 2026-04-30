"""
FOLIO JSONL → WFM (``wfm_profile=smt``) → ``smt_pipeline``, with resume on 503 or partial runs.

State directory (default ``exports/folio_smt_batch``) holds handoffs, WFM completion log,
per-handoff policies, and SMT bundle records. Re-running the same command skips:

- WFM when an example key already has a successful WFM record **and** the handoff file exists.
- SMT when the bundle record under ``smt_bundles/<bundle_id>.json`` has
  ``pipeline_status == "committed"``.

From repo root::

  python -m smt_pipeline.run_folio_wfm_smt_batch --limit 5 --split validation
  python -m smt_pipeline.run_folio_wfm_smt_batch --limit 5 --split validation --dry-run
  python -m smt_pipeline.run_folio_wfm_smt_batch --limit 5 --wfm-delay-sec 5 --smt-delay-sec 30

Requires ``GEMINI_API_KEY``, ``pip install -e .`` from repo root, and WFM test deps
(``pip install -r test_sets/requirements-wfm-test.txt``) for ``google.genai``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_DEFAULT_STATE = _REPO / "exports" / "folio_smt_batch"
_DEFAULT_DATASET_DIR = _REPO / "test_sets" / "datasets" / "folio"


def folio_example_key(*, split: str, line_index: int) -> str:
    return f"folio_{split}_{line_index:05d}"


def folio_row_to_nl(row: dict[str, Any]) -> str:
    premises = row.get("premises") or []
    concl = (row.get("conclusion") or "").strip()
    lines: list[str] = []
    for i, p in enumerate(premises, 1):
        lines.append(f"Premise {i}: {str(p).strip()}")
    lines.append(f"Conclusion: {concl}")
    return "\n".join(lines)


def load_folio_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_wfm_done(path: Path) -> dict[str, dict[str, Any]]:
    """example_key -> latest successful record (handoff_path, bundle_id, ...)."""
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rec.get("success") is True and isinstance(rec.get("example_key"), str):
            out[rec["example_key"]] = rec
    return out


def _is_smt_committed(bundle_out_dir: Path, bundle_id: str) -> bool:
    p = bundle_out_dir / f"{bundle_id}.json"
    if not p.is_file():
        return False
    try:
        rec = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return rec.get("pipeline_status") == "committed"


def append_wfm_completed(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_batch(
    *,
    repo_root: Path,
    state_dir: Path,
    split: str,
    offset: int,
    limit: int,
    wfm_delay_sec: float,
    smt_delay_sec: float,
    dry_run: bool,
) -> int:
    if split not in ("validation", "train"):
        print("error: --split must be validation or train", file=sys.stderr)
        return 2

    folio_path = _DEFAULT_DATASET_DIR / f"folio-{split}.jsonl"
    if not folio_path.is_file():
        print(f"error: dataset not found: {folio_path}", file=sys.stderr)
        return 2

    all_rows = load_folio_rows(folio_path)
    if offset < 0 or offset >= len(all_rows):
        print(f"error: --offset {offset} out of range (n={len(all_rows)})", file=sys.stderr)
        return 2

    end = min(len(all_rows), offset + max(1, limit))
    indices = list(range(offset, end))

    handoff_dir = state_dir / "wfm_handoffs"
    policy_dir = state_dir / "policies"
    bundle_out_dir = state_dir / "smt_bundles"
    wfm_log = state_dir / "wfm_completed.jsonl"

    wfm_done = load_wfm_done(wfm_log)

    if dry_run:
        print(f"split={split}  folio_path={folio_path}")
        print(f"state_dir={state_dir}")
        print(f"line indices [{offset}, {end})  ({len(indices)} examples)")
        for li in indices:
            key = folio_example_key(split=split, line_index=li)
            row = all_rows[li]
            nl = folio_row_to_nl(row)
            hrec = wfm_done.get(key)
            handoff_ok = (
                isinstance(hrec, dict)
                and hrec.get("handoff_path")
                and Path(str(hrec["handoff_path"])).is_file()
            )
            bundle_id = hrec.get("bundle_id") if hrec else None
            smt_ok = bundle_id and _is_smt_committed(bundle_out_dir, str(bundle_id))
            print(
                f"  {key}  label={row.get('label')!r}  "
                f"wfm_cached={handoff_ok}  smt_committed={bool(smt_ok)}  "
                f"chars_nl={len(nl)}"
            )
        return 0

    from wfm_orchestration.e2e_context import create_e2e_context, load_dotenv_for_e2e
    from wfm_orchestration.handoff_artifacts import handoff_write_path
    from wfm_orchestration.orchestrator import run_wfm_registry_e2e
    from wfm_orchestration.run_metadata import new_bundle_id

    from smt_pipeline.config import smt_config_from_env
    from smt_pipeline.pipeline import run_smt_pipeline

    load_dotenv_for_e2e()
    try:
        ctx = create_e2e_context(mock_resolve=True)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        from google import genai  # noqa: F401
    except ImportError:
        print("error: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    handoff_dir.mkdir(parents=True, exist_ok=True)
    policy_dir.mkdir(parents=True, exist_ok=True)
    bundle_out_dir.mkdir(parents=True, exist_ok=True)
    smt_cfg = smt_config_from_env()

    failures = 0
    for j, li in enumerate(indices):
        key = folio_example_key(split=split, line_index=li)
        row = all_rows[li]
        nl = folio_row_to_nl(row)
        label = row.get("label")

        print(f"\n{'='*60}\n[{j + 1}/{len(indices)}] {key}  label={label!r}\n{'='*60}\n", flush=True)

        hrec = wfm_done.get(key)
        handoff_path: Path | None = None
        bundle_id: str | None = None

        if (
            isinstance(hrec, dict)
            and hrec.get("success")
            and hrec.get("handoff_path")
            and Path(str(hrec["handoff_path"])).is_file()
        ):
            handoff_path = Path(str(hrec["handoff_path"])).resolve()
            bundle_id = str(hrec.get("bundle_id") or "")
            print(f"[wfm] skip (cached handoff) -> {handoff_path.name}", flush=True)
        else:
            if j > 0 and wfm_delay_sec > 0:
                time.sleep(wfm_delay_sec)
            bid = new_bundle_id(prefix="folio_smt")
            hpath = handoff_write_path(repo_root, bid, handoff_dir=handoff_dir)
            try:
                out = run_wfm_registry_e2e(
                    initial_user_text=nl,
                    client=ctx.client,
                    model=ctx.model,
                    temperature=ctx.temperature,
                    max_output_tokens=ctx.max_output_tokens,
                    thinking_level=ctx.thinking_level,
                    registry_session=ctx.registry_session,
                    llm_complete=ctx.llm_complete,
                    bundle_id=bid,
                    bundle_id_prefix="folio_smt",
                    handoff_json=hpath,
                    repo_root=repo_root,
                    handoff_dir=handoff_dir,
                    persist_handoff=True,
                    example_id=key,
                    auto_accept=True,
                    skip_registry=True,
                    auto_artifacts=False,
                    wfm_profile="smt",
                    print_fn=print,
                    stderr=sys.stderr,
                )
            except Exception as e:
                failures += 1
                print(f"[wfm] FAILED {key}: {e}", file=sys.stderr)
                traceback.print_exc()
                continue

            if out is None or getattr(out, "bundle", None) is None:
                failures += 1
                print(f"[wfm] FAILED {key}: no handoff (abort or LIMIT_EXCEEDED)", file=sys.stderr)
                continue

            b = out.bundle
            bundle_id = b.bundle_id
            handoff_path = hpath.resolve()
            if not handoff_path.is_file():
                failures += 1
                print(f"[wfm] FAILED {key}: expected handoff at {handoff_path}", file=sys.stderr)
                continue

            rec = {
                "success": True,
                "example_key": key,
                "split": split,
                "line_index": li,
                "label": label,
                "bundle_id": bundle_id,
                "handoff_path": str(handoff_path),
                "utc": datetime.now(timezone.utc).isoformat(),
            }
            append_wfm_completed(wfm_log, rec)
            wfm_done[key] = rec
            print(f"[wfm] ok -> {handoff_path.name}  bundle_id={bundle_id}", flush=True)

        assert handoff_path is not None and handoff_path.is_file()
        assert bundle_id

        if _is_smt_committed(bundle_out_dir, bundle_id):
            print(f"[smt] skip (already committed) bundle_id={bundle_id}", flush=True)
            continue

        if j > 0 and smt_delay_sec > 0:
            time.sleep(smt_delay_sec)

        policy_path = policy_dir / f"{handoff_path.stem}.smt2"
        try:
            res = run_smt_pipeline(
                handoff_path=handoff_path,
                policy_model_path=policy_path,
                bundle_out_dir=bundle_out_dir,
                cfg=smt_cfg,
            )
        except Exception as e:
            failures += 1
            print(f"[smt] FAILED {key}: {e}", file=sys.stderr)
            traceback.print_exc()
            continue

        if res.status != "success":
            failures += 1
            print(f"[smt] FAILED {key}: {res.failure_reason}", file=sys.stderr)
            continue

        print(f"[smt] ok -> policy={policy_path.name}  record={res.bundle_record_path}", flush=True)

    print(f"\nDone. Failures this run: {failures}. State: {state_dir}")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="FOLIO NL → WFM (smt profile) → smt_pipeline; resume-safe state under exports/folio_smt_batch."
    )
    ap.add_argument("--split", choices=("validation", "train"), default="validation")
    ap.add_argument("--offset", type=int, default=0, help="First line index in the JSONL (0-based).")
    ap.add_argument("--limit", type=int, default=5, help="Number of consecutive rows to process.")
    ap.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help=f"Directory for handoffs, logs, policies (default: {_DEFAULT_STATE})",
    )
    ap.add_argument("--wfm-delay-sec", type=float, default=0.0, help="Pause before each WFM call (after the first).")
    ap.add_argument(
        "--smt-delay-sec",
        type=float,
        default=0.0,
        help="Pause before each smt_pipeline call (after the first).",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print plan and cache status only.")
    args = ap.parse_args(argv)

    state_dir = args.state_dir if args.state_dir is not None else _DEFAULT_STATE
    return run_batch(
        repo_root=_REPO,
        state_dir=state_dir.resolve(),
        split=args.split,
        offset=args.offset,
        limit=args.limit,
        wfm_delay_sec=max(0.0, args.wfm_delay_sec),
        smt_delay_sec=max(0.0, args.smt_delay_sec),
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
