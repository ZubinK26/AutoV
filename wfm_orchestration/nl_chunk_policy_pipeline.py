"""
Chunked NL file → WFM (Agents 1–3) → one shared ClinCon policy (``asp_pipeline``).

**Spec alignment**

- **Shared policy, sequential bundles:** :mod:`docs.pipeline_wfm_to_asp` §10 — point one ``--policy-model``
  and run handoffs in sequence; each commit appends a block. The formalizer always receives
  the **full existing** ``.lp`` in ``<existing_policy_model>`` (see
  :func:`asp_pipeline.llm_steps.build_formalizer_user_message` and
  :file:`asp_pipeline/prompts/formalizer_new.md` — *Reuse every predicate/constant name that
  already appears in EXISTING POLICY verbatim.*).

- **Size caps:** Per formalization, ``ASP_PIPELINE_RULE_CAP`` and ``ASP_PIPELINE_CONTEXT_CHAR_LIMIT``
  apply to *existing policy + this bundle* (:mod:`asp_pipeline.config`).

**This CLI**

- Reads a UTF-8 NL file: **one rule per non-empty line** (lines starting with ``#`` are comments).
- Each invocation processes up to ``--rules-per-chunk`` rules starting at a cursor stored in
  ``<work_dir>/nl_chunk_progress.json`` (idempotent: already-processed lines are not re-run).
- After each successful policy commit, copies the policy ``.lp`` to ``<work_dir>/policy_snapshots/``
  for diffing (duplicate-identifier review).

- **503 / partial failure:** If WFM produces a handoff but ASP (Gemini/Clingo) fails, the next run **skips
  WFM** and retries **only** ASP for that same chunk, using the saved handoff and ``bundle_id`` in
  ``pending_asp`` — so the policy still grows in **NL line order** and the formalizer does not
  re-order chunks. ``next_rule_index`` advances only after a full commit.

From repo root::

  python -m wfm_orchestration.nl_chunk_policy_pipeline --nl-file path/to/rules.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

PROGRESS_VERSION = "nl_chunk_progress_v1"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_nl_rules(nl_text: str) -> list[str]:
    """
    One rule per non-empty line. Full-line ``#`` comments and ``---`` separators are skipped.
    """
    out: list[str] = []
    for line in nl_text.splitlines():
        t = line.strip()
        if not t or t.startswith("#"):
            continue
        if t == "---":
            continue
        out.append(line.strip())
    return out


@dataclass
class NlChunkProgress:
    schema_version: str = PROGRESS_VERSION
    nl_path_posix: str = ""
    nl_sha256: str = ""
    rules_per_chunk: int = 10
    next_rule_index: int = 0
    chunk_records: list[dict[str, Any]] = field(default_factory=list)
    work_dir_posix: str = ""
    #: Set after WFM writes a handoff; cleared after ASP commits. Rerun = ASP only (same handoff, same order).
    pending_asp: dict[str, Any] | None = None

    def to_jsonable(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> NlChunkProgress:
        p = d.get("pending_asp")
        return cls(
            schema_version=str(d.get("schema_version", PROGRESS_VERSION)),
            nl_path_posix=str(d.get("nl_path_posix", "")),
            nl_sha256=str(d.get("nl_sha256", "")),
            rules_per_chunk=int(d.get("rules_per_chunk", 10)),
            next_rule_index=int(d.get("next_rule_index", 0)),
            chunk_records=list(d.get("chunk_records") or []),
            work_dir_posix=str(d.get("work_dir_posix", "")),
            pending_asp=p if isinstance(p, dict) else None,
        )


def load_or_init_progress(
    path: Path,
    *,
    nl_path: Path,
    nl_hash: str,
    rules_per_chunk: int,
    work_dir: Path,
    force_reset: bool,
) -> NlChunkProgress:
    work_dir = work_dir.resolve()
    nl_path = nl_path.resolve()
    if not path.is_file() or force_reset:
        return NlChunkProgress(
            nl_path_posix=nl_path.as_posix(),
            nl_sha256=nl_hash,
            rules_per_chunk=rules_per_chunk,
            next_rule_index=0,
            chunk_records=[],
            work_dir_posix=work_dir.as_posix(),
            pending_asp=None,
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    p = NlChunkProgress.from_dict(raw)
    if p.nl_sha256 != nl_hash and not force_reset:
        raise ValueError(
            f"NL file content changed (stored sha256 {p.nl_sha256[:12]}… vs current {nl_hash[:12]}…). "
            "Use --reset-progress to restart from rule 0, or use a different --work-dir."
        )
    if p.rules_per_chunk != rules_per_chunk:
        raise ValueError(
            f"Progress file has rules_per_chunk={p.rules_per_chunk}; this run uses {rules_per_chunk}. "
            "Use --reset-progress or match --rules-per-chunk."
        )
    p.nl_path_posix = nl_path.as_posix()
    p.work_dir_posix = work_dir.as_posix()
    return p


def save_progress(path: Path, p: NlChunkProgress) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(p.to_jsonable(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def format_chunk_for_wfm(
    rules: list[str],
    *,
    start_index: int,
    file_label: str,
) -> str:
    """User NL for WFM: numbered chunk with light provenance (no SymTex benchmark banner)."""
    parts = [
        f"Incremental policy ruleset chunk from file {file_label!r} (1-based global rule indices"
        f" {start_index + 1}–{start_index + len(rules)}).",
        "",
        "Rules in this chunk:",
    ]
    for j, r in enumerate(rules):
        parts.append(f"{start_index + j + 1}. {r}")
    return "\n".join(parts)


def _heal_stale_pending_asp(
    prog: NlChunkProgress,
    *,
    asp_bundles: Path,
    progress_path: Path,
    print_fn: Any,
) -> bool:
    """
    If ``pending_asp`` points to a chunk that is already ``committed`` in ``asp_bundles`` (e.g. crash
    after commit but before clearing pending), advance cursor and clear pending. Returns True if healed.
    """
    from wfm_orchestration.symtex_ground_truth_utils import is_asp_pipeline_committed

    pend = prog.pending_asp
    if not isinstance(pend, dict):
        return False
    bid = pend.get("bundle_id")
    if not isinstance(bid, str) or not bid:
        return False
    if not is_asp_pipeline_committed(bundle_out_dir=asp_bundles, bundle_id=bid):
        return False
    start = int(pend["rule_index_start"])
    end = int(pend["rule_index_end"])
    chunk_seq = int(pend.get("chunk_seq", len(prog.chunk_records)))
    if not any(isinstance(x, dict) and x.get("bundle_id") == bid for x in prog.chunk_records):
        prog.chunk_records.append(
            {
                "chunk_seq": chunk_seq,
                "rule_index_start": start,
                "rule_index_end": end,
                "bundle_id": bid,
                "healed": True,
                "note": "Recovered: ASP was already committed; pending_asp was stale on disk.",
            }
        )
    prog.next_rule_index = end
    prog.pending_asp = None
    save_progress(progress_path, prog)
    print_fn(
        f"[heal] Recovered completed chunk (bundle_id={bid}); next_rule_index={end}. "
        "A previous run likely exited after policy commit but before progress save."
    )
    return True


def snapshot_policy(
    policy_lp: Path,
    *,
    snapshot_dir: Path,
    chunk_seq: int,
    bundle_id: str,
) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"policy_after_chunk_{chunk_seq:04d}_{ts}_{bundle_id}.lp"
    out = snapshot_dir / name
    if policy_lp.is_file():
        shutil.copy2(policy_lp, out)
    else:
        out.write_text("", encoding="utf-8")
    latest = snapshot_dir / "policy_latest.lp"
    if policy_lp.is_file():
        shutil.copy2(policy_lp, latest)
    return out


def run_chunk_pipeline(
    *,
    repo_root: Path,
    nl_file: Path,
    work_dir: Path,
    policy_model: Path,
    rules_per_chunk: int,
    dry_run: bool,
    force_reset: bool,
    print_fn: Any = print,
) -> int:
    nl_file = nl_file.resolve()
    work_dir = work_dir.resolve()
    policy_model = policy_model.resolve()
    if not nl_file.is_file():
        print_fn(f"error: NL file not found: {nl_file}", file=sys.stderr)
        return 2

    nl_hash = _sha256_file(nl_file)
    nl_body = nl_file.read_text(encoding="utf-8")
    all_rules = parse_nl_rules(nl_body)
    total = len(all_rules)
    if total == 0:
        print_fn("error: no rules after parsing (non-empty, non-# comment lines).", file=sys.stderr)
        return 2

    progress_path = work_dir / "nl_chunk_progress.json"
    try:
        prog = load_or_init_progress(
            progress_path,
            nl_path=nl_file,
            nl_hash=nl_hash,
            rules_per_chunk=rules_per_chunk,
            work_dir=work_dir,
            force_reset=force_reset,
        )
    except ValueError as e:
        print_fn(f"error: {e}", file=sys.stderr)
        return 2

    wfm_dir = work_dir / "wfm_handoffs"
    asp_bundles = work_dir / "asp_bundles"
    snap_dir = work_dir / "policy_snapshots"
    wfm_dir.mkdir(parents=True, exist_ok=True)
    asp_bundles.mkdir(parents=True, exist_ok=True)
    policy_model.parent.mkdir(parents=True, exist_ok=True)

    if not dry_run:
        for _ in range(4):
            if not _heal_stale_pending_asp(
                prog, asp_bundles=asp_bundles, progress_path=progress_path, print_fn=print_fn
            ):
                break

    start = prog.next_rule_index
    if start >= total:
        print_fn(
            f"Nothing to do: all {total} rule(s) already processed (next_index={start}). "
            f"Use --reset-progress to restart."
        )
        return 0

    end = min(start + rules_per_chunk, total)
    chunk_rules = all_rules[start:end]
    chunk_seq = len(prog.chunk_records)
    if dry_run:
        pend = prog.pending_asp
        resume = (
            isinstance(pend, dict)
            and int(pend.get("rule_index_start", -1)) == start
            and int(pend.get("rule_index_end", -1)) == end
        )
        mode = "resume ASP only (handoff on disk)" if resume else "full WFM then ASP"
        print_fn(
            f"dry_run: would process rules [{start}, {end}) ({len(chunk_rules)} rules), "
            f"chunk_seq={chunk_seq}, mode={mode}, policy={policy_model}"
        )
        for i, r in enumerate(chunk_rules):
            print_fn(f"  {start + i + 1}. {r[:120]}{'…' if len(r) > 120 else ''}")
        return 0

    from wfm_orchestration.e2e_context import create_e2e_context
    from wfm_orchestration.orchestrator import run_wfm_registry_e2e
    from wfm_orchestration.run_metadata import new_bundle_id
    from wfm_orchestration.handoff_artifacts import handoff_write_path
    from asp_pipeline.config import asp_config_from_env
    from asp_pipeline.pipeline import run_asp_pipeline

    pend = prog.pending_asp
    resume_asp_only = (
        isinstance(pend, dict)
        and int(pend.get("rule_index_start", -1)) == start
        and int(pend.get("rule_index_end", -1)) == end
    )
    bundle_id: str
    handoff_path: Path

    if resume_asp_only:
        bundle_id = str(pend["bundle_id"])
        rel = str(pend.get("handoff_relposix", ""))
        handoff_path = (repo_root / rel) if rel else Path(str(pend.get("handoff_abspath", "")))
        if not handoff_path.is_file():
            print_fn(
                f"error: pending_asp references missing handoff {handoff_path}. "
                "Remove pending_asp from progress file or use --reset-progress.",
                file=sys.stderr,
            )
            return 2
        try:
            ho = json.loads(handoff_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print_fn(f"error: cannot read handoff: {e}", file=sys.stderr)
            return 2
        if (ho.get("bundle_id") or "") != bundle_id:
            print_fn(
                "error: handoff bundle_id does not match pending_asp (do not edit handoff manually).",
                file=sys.stderr,
            )
            return 2
        chunk_seq = int(pend.get("chunk_seq", chunk_seq))
        print_fn(
            f"\n--- Resume rules {start + 1}–{end} of {total}: ASP only "
            f"(reusing WFM handoff, bundle_id={bundle_id}) ---\n"
        )
    else:
        if isinstance(pend, dict) and not resume_asp_only:
            print_fn(
                "error: progress has stale pending_asp for a different rule range than the current chunk. "
                "Fix nl_chunk_progress.json or use --reset-progress.",
                file=sys.stderr,
            )
            return 2
        try:
            ctx = create_e2e_context(mock_resolve=True)
        except RuntimeError as e:
            print_fn(f"error: {e}", file=sys.stderr)
            return 2

        bundle_id = new_bundle_id(prefix="nlchunk")
        chunk_text = format_chunk_for_wfm(
            chunk_rules, start_index=start, file_label=nl_file.name
        )
        handoff_path = handoff_write_path(repo_root, bundle_id, handoff_dir=wfm_dir)

        print_fn(f"\n--- NL chunk: rules {start + 1}–{end} of {total}  bundle_id={bundle_id} ---\n")

        dev = run_wfm_registry_e2e(
            initial_user_text=chunk_text,
            client=ctx.client,
            model=ctx.model,
            temperature=ctx.temperature,
            max_output_tokens=ctx.max_output_tokens,
            thinking_level=ctx.thinking_level,
            registry_session=ctx.registry_session,
            llm_complete=ctx.llm_complete,
            bundle_id=bundle_id,
            bundle_id_prefix="nlchunk",
            handoff_json=handoff_path,
            repo_root=repo_root,
            handoff_dir=wfm_dir,
            persist_handoff=True,
            skip_registry=True,
            auto_accept=True,
            auto_artifacts=False,
            example_id=f"nl_chunk_{nl_file.stem}",
            print_fn=print_fn,
        )

        if dev is None:
            print_fn("WFM e2e failed (no handoff). Progress not updated.", file=sys.stderr)
            return 1

        if not handoff_path.is_file():
            print_fn(f"error: expected handoff at {handoff_path}", file=sys.stderr)
            return 1

        try:
            hrel = str(handoff_path.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            hrel = str(handoff_path.resolve())
        prog.pending_asp = {
            "rule_index_start": start,
            "rule_index_end": end,
            "chunk_seq": chunk_seq,
            "bundle_id": bundle_id,
            "handoff_relposix": hrel,
        }
        save_progress(progress_path, prog)
        print_fn("[progress] Saved pending_asp — if ASP fails (e.g. 503), rerun to retry ASP only.\n")

    cfg = asp_config_from_env()
    res = run_asp_pipeline(
        handoff_path=handoff_path,
        policy_model_path=policy_model,
        bundle_out_dir=asp_bundles,
        cfg=cfg,
    )
    if res.status != "success":
        print_fn(
            f"ASP pipeline failed: {res.failure_reason or 'failed'}  bundle_record={res.bundle_record_path}",
            file=sys.stderr,
        )
        print_fn(
            "pending_asp is on disk — run the same command again to retry ASP only (same handoff, same order).",
            file=sys.stderr,
        )
        return 1

    snap = snapshot_policy(policy_model, snapshot_dir=snap_dir, chunk_seq=chunk_seq, bundle_id=bundle_id)
    print_fn(f"\nPolicy snapshot: {snap}\n")

    prog.pending_asp = None
    prog.next_rule_index = end
    try:
        hrel = str(handoff_path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        hrel = str(handoff_path.resolve())
    prog.chunk_records.append(
        {
            "chunk_seq": chunk_seq,
            "rule_index_start": start,
            "rule_index_end": end,
            "bundle_id": bundle_id,
            "handoff_relposix": hrel,
            "policy_snapshot": snap.as_posix(),
            "committed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    save_progress(progress_path, prog)
    print_fn(
        f"OK: advanced progress next_rule_index={prog.next_rule_index}/{total}  "
        f"({total - prog.next_rule_index} rule(s) remain)."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Process the next N NL rules (chunk) through WFM + asp_pipeline into one shared policy .lp."
    )
    p.add_argument(
        "--nl-file",
        type=Path,
        required=True,
        help="UTF-8 file: one natural-language rule per non-empty line (# comments ignored).",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Progress, handoffs, asp bundle records, policy snapshots (default: exports/nl_chunk_runs/<nl stem>).",
    )
    p.add_argument(
        "--policy-model",
        type=Path,
        default=None,
        help="Target shared policy .lp (default: <work_dir>/policy_model.lp).",
    )
    p.add_argument("--rules-per-chunk", type=int, default=10)
    p.add_argument(
        "--reset-progress",
        action="store_true",
        help="Ignore existing nl_chunk_progress.json and start from rule 0.",
    )
    p.add_argument("--dry-run", action="store_true", help="Show next chunk only; no API and no commit.")
    args = p.parse_args(argv)

    repo = _REPO
    nl = (repo / args.nl_file) if not args.nl_file.is_absolute() else args.nl_file
    stem = nl.stem
    work = args.work_dir
    if work is None:
        work = repo / "exports" / "nl_chunk_runs" / stem
    else:
        work = repo / work if not work.is_absolute() else work

    pol = args.policy_model
    if pol is None:
        pol = work / "policy_model.lp"
    else:
        pol = repo / pol if not pol.is_absolute() else pol

    if not args.dry_run:
        from wfm_orchestration.e2e_context import load_dotenv_for_e2e

        load_dotenv_for_e2e()

    return run_chunk_pipeline(
        repo_root=repo,
        nl_file=nl,
        work_dir=work,
        policy_model=pol,
        rules_per_chunk=max(1, int(args.rules_per_chunk)),
        dry_run=args.dry_run,
        force_reset=args.reset_progress,
    )


if __name__ == "__main__":
    raise SystemExit(main())
