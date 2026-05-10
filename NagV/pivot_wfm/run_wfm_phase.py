"""Run chunked pivot-profile WFM until all NL rules have handoffs (Phase 0)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from wfm_orchestration.handoff_artifacts import handoff_write_path
from wfm_orchestration.nl_chunk_policy_pipeline import format_chunk_for_wfm, parse_nl_rules
from wfm_orchestration.nl_chunk_smt_policy_pipeline import load_or_init_progress, save_progress
from wfm_orchestration.run_metadata import new_bundle_id


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _max_wfm_coverage_attempts() -> int:
    raw = os.getenv("PIVOT_WFM_COVERAGE_MAX_WFM_ATTEMPTS", "3").strip()
    try:
        n = int(raw)
        return max(1, min(n, 20))
    except ValueError:
        return 3


def _unlink_if_exists(path: Path) -> None:
    if path.is_file():
        path.unlink()


def _append_coverage_log(work_dir: Path, record: dict[str, Any]) -> None:
    path = work_dir / "pivot_wfm_coverage_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as lf:
        lf.write(json.dumps(record, ensure_ascii=False) + "\n")


def _pivot_chunk_agent2_line_budget_footer(rule_count: int) -> str:
    """
    Agent 2 must not over-decompose chunk rules: coverage expects one handoff row per chunk rule.
    """
    if rule_count <= 0:
        return ""
    return (
        "\n\n[Pivot pipeline — Agent 2 output shape]\n"
        f"This chunk has exactly {rule_count} policy rules (see numbered list above). "
        f"Your SUCCESS output must contain **exactly {rule_count}** numbered lines "
        f"(1. through {rule_count}.), **one line per input rule** in order. "
        "Do not add another numbered line by splitting one input rule into multiple statements. "
        "Do not merge two input rules into one numbered line."
    )


def _format_pivot_chunk_text(chunk_rules: list[str], *, start: int, file_label: str) -> str:
    return format_chunk_for_wfm(
        chunk_rules, start_index=start, file_label=file_label
    ) + _pivot_chunk_agent2_line_budget_footer(len(chunk_rules))


def run_pivot_wfm_until_complete(
    *,
    repo_root: Path,
    nl_file: Path,
    work_dir: Path,
    rules_per_chunk: int,
    reset_progress: bool,
    print_fn: Callable[..., None] = print,
    interactive_policy: bool = False,
    input_fn: Callable[[str], str] | None = None,
) -> int:
    """``wfm_profile=pivot`` handoffs only (no SMT / NagV formalizer)."""
    from pivot_pipeline.exceptions import PivotPipelineUserAbort
    from pivot_pipeline.llm import pivot_llm_complete
    from pivot_pipeline.policy_gates import PROCEED_INCOMPLETE_TOKEN
    from pivot_wfm.handoff_coverage import (
        ChunkCoverageReport,
        analyze_chunk_handoff_coverage,
        patch_handoff_inject_missing_rules,
    )
    from pivot_wfm.wfm_chunk_scope_rewrite import run_wfm_chunk_scope_rewrite
    from pivot_pipeline.llm import get_pivot_gemini_model, get_pivot_gemini_thinking_level_str
    from wfm_orchestration.e2e_context import create_e2e_context
    from wfm_orchestration.orchestrator import run_wfm_registry_e2e

    if input_fn is None:
        input_fn = input

    nl_file = nl_file.resolve()
    work_dir = work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    if not nl_file.is_file():
        print_fn(f"error: NL file not found: {nl_file}", file=sys.stderr)
        return 2

    if reset_progress:
        _unlink_if_exists(work_dir / "pivot_wfm_effective_source.nl")
        _unlink_if_exists(work_dir / "pivot_wfm_dropped_rules.jsonl")
        _unlink_if_exists(work_dir / "pivot_wfm_coverage_log.jsonl")
        _unlink_if_exists(work_dir / "pivot_wfm_phase0_meta.json")

    nl_hash = _sha256_file(nl_file)
    body = nl_file.read_text(encoding="utf-8")
    all_rules = parse_nl_rules(body)
    total = len(all_rules)

    if total == 0:
        print_fn("error: no rules after parsing NL.", file=sys.stderr)
        return 2

    progress_path = work_dir / "nl_chunk_progress.json"
    try:
        prog = load_or_init_progress(
            progress_path,
            nl_path=nl_file,
            nl_hash=nl_hash,
            rules_per_chunk=rules_per_chunk,
            work_dir=work_dir,
            force_reset=reset_progress,
        )
    except ValueError as e:
        print_fn(f"error: {e}", file=sys.stderr)
        return 2

    wfm_dir = work_dir / "wfm_handoffs"
    wfm_dir.mkdir(parents=True, exist_ok=True)

    chunks_this_invocation = 0
    dropped_any = False
    max_wfm = _max_wfm_coverage_attempts()
    llm = pivot_llm_complete

    def commit_chunk_record(
        *,
        start: int,
        end: int,
        chunk_seq: int,
        bundle_id: str,
        handoff_path: Path,
    ) -> None:
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
                "pivot_wfm_only": True,
            }
        )
        prog.next_rule_index = end
        prog.pending_smt = None
        save_progress(progress_path, prog)

    def print_coverage_report(cov: ChunkCoverageReport) -> None:
        print_fn(
            f"[pivot WFM coverage] expected indices "
            f"{cov.rule_index_start}..{cov.rule_index_end_exclusive - 1}, "
            f"forward={cov.forward_count}, missing={list(cov.missing_indices)}, "
            f"duplicates={list(cov.duplicate_indices)}, extras={list(cov.extra_indices)}"
        )

    while prog.next_rule_index < len(all_rules):
        start = prog.next_rule_index
        end = min(start + rules_per_chunk, len(all_rules))
        chunk_seq = len(prog.chunk_records)
        chunk_rules = all_rules[start:end]
        chunk_text = _format_pivot_chunk_text(chunk_rules, start=start, file_label=nl_file.name)

        wfm_runs = 0
        committed = False

        while not committed:
            wfm_runs += 1
            bundle_id = new_bundle_id(prefix="pivotwfm")
            handoff_path = handoff_write_path(repo_root, bundle_id, handoff_dir=wfm_dir)

            print_fn(f"\n--- Pivot WFM chunk: rules {start + 1}–{end} of {len(all_rules)}  bundle_id={bundle_id} ---\n")
            if wfm_runs > 1:
                print_fn(f"(WFM attempt {wfm_runs}/{max_wfm} for this chunk)\n")

            try:
                ctx = create_e2e_context(
                    mock_resolve=True,
                    gemini_model_override=get_pivot_gemini_model(),
                    gemini_thinking_level_token=get_pivot_gemini_thinking_level_str(),
                )
            except RuntimeError as e:
                print_fn(f"error: {e}", file=sys.stderr)
                return 2

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
                bundle_id_prefix="pivotwfm",
                handoff_json=handoff_path,
                repo_root=repo_root,
                handoff_dir=wfm_dir,
                persist_handoff=True,
                skip_registry=True,
                auto_accept=True,
                auto_artifacts=False,
                example_id=f"pivot_{nl_file.stem}",
                wfm_profile="pivot",
                global_rule_index_start=start,
                print_fn=print_fn,
            )

            if dev is None:
                print_fn("WFM failed (no handoff).", file=sys.stderr)
                return 1
            if not handoff_path.is_file():
                print_fn(f"error: missing handoff at {handoff_path}", file=sys.stderr)
                return 1

            cov = analyze_chunk_handoff_coverage(handoff_path, start, end)
            if cov.ok:
                _append_coverage_log(
                    work_dir,
                    {
                        "event": "chunk_coverage_ok",
                        "bundle_id": bundle_id,
                        "rule_index_start": start,
                        "rule_index_end": end,
                        "wfm_attempt": wfm_runs,
                    },
                )
                commit_chunk_record(
                    start=start,
                    end=end,
                    chunk_seq=chunk_seq,
                    bundle_id=bundle_id,
                    handoff_path=handoff_path,
                )
                chunks_this_invocation += 1
                committed = True
                print_fn(f"OK: pivot WFM chunk committed; next_rule_index={prog.next_rule_index}/{len(all_rules)}\n")
                break

            _append_coverage_log(
                work_dir,
                {
                    "event": "chunk_coverage_fail",
                    "bundle_id": bundle_id,
                    "rule_index_start": start,
                    "rule_index_end": end,
                    "wfm_attempt": wfm_runs,
                    "missing_indices": list(cov.missing_indices),
                    "duplicate_indices": list(cov.duplicate_indices),
                    "extra_indices": list(cov.extra_indices),
                },
            )

            print_fn("\n[pivot WFM] Chunk coverage check failed.\n")
            print_coverage_report(cov)

            if not interactive_policy:
                print_fn(
                    "\nRe-run with --interactive-policy for scope-rewrite + retry, "
                    "or fix NL / WFM prompts.\n",
                    file=sys.stderr,
                )
                return 3

            if wfm_runs < max_wfm:
                rewrite_accepted = False
                while True:
                    try:
                        rewritten = run_wfm_chunk_scope_rewrite(
                            chunk_rules,
                            rule_index_start=start,
                            rule_index_end_exclusive=end,
                            file_label=nl_file.name,
                            coverage_report=cov,
                            handoff_path=handoff_path,
                            llm=llm,
                        )
                    except Exception as ex:  # noqa: BLE001
                        print_fn(f"[pivot WFM] scope rewrite failed: {ex}\n")
                        ans = input_fn(
                            "[r] Retry rewrite prompt, [g] Give up (final options): "
                        ).strip().lower()
                        if ans in ("g", "give-up", "give up"):
                            break
                        continue

                    print_fn(
                        "\n[policy edit — chunk rewrite]\n"
                        "Accepting **y** replaces the **source text** for this chunk’s rule lines with the "
                        "proposed lines below. That becomes the **authoritative working policy** for Phase 0 "
                        "aggregation and for **later extract / formalization** — not a cosmetic-only change.\n"
                    )
                    print_fn("\n**Proposed chunk rewrite (LLM)** — one rule per line:\n")
                    for i, rtxt in enumerate(rewritten, start=1):
                        print_fn(f"  {start + i}. {rtxt}")
                    print_fn("")
                    ans = input_fn(
                        "Accept rewrite and re-run WFM? [y/N/g] (g = final options): "
                    ).strip().lower()
                    if ans in ("g", "give-up", "give up"):
                        break
                    if ans not in ("y", "yes"):
                        continue
                    for j, rtxt in enumerate(rewritten):
                        all_rules[start + j] = rtxt
                    chunk_rules = all_rules[start:end]
                    chunk_text = _format_pivot_chunk_text(chunk_rules, start=start, file_label=nl_file.name)
                    rewrite_accepted = True
                    break

                if rewrite_accepted:
                    continue

            # Final options: abort, drop missing, or inject
            print_fn(
                "\nCoverage still unsatisfied after this chunk’s repair budget.\n"
                f"[a] Abort run\n"
                f"[d] Drop missing rule line(s) from the policy and retry this chunk "
                f"(missing indices: {list(cov.missing_indices)})\n"
                f"Type {PROCEED_INCOMPLETE_TOKEN} to inject raw source lines into the handoff for "
                f"missing indices and continue (see scope_report on those rows).\n"
            )
            final = input_fn("Choice: ").strip()
            if final == PROCEED_INCOMPLETE_TOKEN:
                try:
                    cov2 = patch_handoff_inject_missing_rules(
                        handoff_path,
                        rule_index_start=start,
                        rule_index_end_exclusive=end,
                        all_rules=all_rules,
                    )
                except ValueError as ex:
                    print_fn(f"error: inject failed: {ex}", file=sys.stderr)
                    return 1
                if not cov2.ok:
                    print_fn(f"error: handoff still not coverage-clean: {cov2}", file=sys.stderr)
                    return 1
                _append_coverage_log(
                    work_dir,
                    {
                        "event": "chunk_coverage_inject",
                        "bundle_id": bundle_id,
                        "rule_index_start": start,
                        "rule_index_end": end,
                    },
                )
                commit_chunk_record(
                    start=start,
                    end=end,
                    chunk_seq=chunk_seq,
                    bundle_id=bundle_id,
                    handoff_path=handoff_path,
                )
                chunks_this_invocation += 1
                committed = True
                print_fn(f"OK: chunk committed after PROCEED_INCOMPLETE inject; next_rule_index={prog.next_rule_index}/{len(all_rules)}\n")
                break

            if final.lower() in ("d", "drop"):
                drop_ix = sorted(cov.missing_indices, reverse=True)
                if not drop_ix:
                    print_fn("error: no missing indices to drop.", file=sys.stderr)
                    return 1
                drop_path = work_dir / "pivot_wfm_dropped_rules.jsonl"
                for di in drop_ix:
                    if not (start <= di < end):
                        print_fn(f"error: missing index {di} not in current chunk span.", file=sys.stderr)
                        return 1
                    dropped_line = all_rules.pop(di)
                    dropped_any = True
                    rec = {
                        "rule_index_dropped": di,
                        "line": dropped_line,
                        "reason": "operator_drop_wfm_coverage",
                        "chunk_bundle_id": bundle_id,
                    }
                    with drop_path.open("a", encoding="utf-8") as lf:
                        lf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                if start >= len(all_rules):
                    prog.next_rule_index = len(all_rules)
                    save_progress(progress_path, prog)
                    committed = True
                    print_fn("[pivot WFM] Dropped the remainder of the policy; Phase 0 complete.\n")
                    break
                end = min(start + rules_per_chunk, len(all_rules))
                chunk_rules = all_rules[start:end]
                if not chunk_rules:
                    prog.next_rule_index = len(all_rules)
                    save_progress(progress_path, prog)
                    committed = True
                    print_fn("[pivot WFM] No rules left in this chunk after drop; advancing.\n")
                    break
                chunk_text = _format_pivot_chunk_text(chunk_rules, start=start, file_label=nl_file.name)
                wfm_runs = 0
                print_fn(f"[pivot WFM] Dropped {len(drop_ix)} rule(s); retrying chunk with {len(chunk_rules)} line(s).\n")
                continue

            raise PivotPipelineUserAbort(
                f"pivot WFM chunk coverage repair exhausted or aborted (rules {start + 1}–{end})"
            )

    if dropped_any:
        (work_dir / "pivot_wfm_effective_source.nl").write_text(
            "\n\n".join(all_rules) + "\n",
            encoding="utf-8",
        )
    elif chunks_this_invocation > 0:
        _unlink_if_exists(work_dir / "pivot_wfm_effective_source.nl")

    if chunks_this_invocation == 0:
        print_fn(
            f"[pivot WFM] Phase 0 skipped: progress file already has all {total} rule(s) marked done "
            f"for this NL file (no chunks run this invocation).\n"
            f"  → To **re-run WFM** (and per-chunk coverage repair), pass **--reset-progress** with the same "
            f"--work-dir. Otherwise existing handoffs are reused and can mismatch --input rule count.\n"
        )
    else:
        print_fn(
            f"[pivot WFM] Finished Phase 0 for all {len(all_rules)} rule(s) in effect "
            f"({chunks_this_invocation} chunk(s) processed this run)."
        )
    (work_dir / "pivot_wfm_phase0_meta.json").write_text(
        json.dumps(
            {
                "schema_version": "pivot_wfm_phase0_meta_v1",
                "chunks_this_invocation": chunks_this_invocation,
                "source_rule_count_at_start": total,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0
