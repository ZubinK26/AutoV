"""CLI: ``scope-rewriter`` — pre-WFM reference → plain NL + sidecar."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ``pivot_pipeline`` package lives under ``NagV/pivot_pipeline``; ``registry_stage`` under repo root.
_script = Path(__file__).resolve()
_AUTOV_ROOT = _script.parents[2]
_NAGV_ROOT = _script.parents[1]
for _p in (_AUTOV_ROOT, _NAGV_ROOT):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from pivot_pipeline.paths import resolve_existing_user_file
from pivot_pipeline.scope_rewriter_agent import (
    load_scope_rewriter_system_prompt,
    max_rounds_default,
    normalize_input_mode,
    run_scope_rewriter_round,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Pre-WFM Scope Rewriter: rewrite a reference Markdown/text file into plain rules "
            "aligned with pivot v1 encodability, with JSON sidecar and human review loop."
        )
    )
    p.add_argument(
        "--reference",
        type=Path,
        required=True,
        help="Reference document path (UTF-8), e.g. policy_notes.md",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        required=True,
        help="Output directory (writes scope_rewriter/latest.nl + latest.json)",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=_AUTOV_ROOT,
        help="AutoV repo root",
    )
    p.add_argument(
        "--max-rounds",
        type=int,
        default=None,
        help="Cap agent calls in interactive mode (default env SCOPE_REWRITER_MAX_ROUNDS or 20)",
    )
    p.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run a single agent round and exit (CI / scripting)",
    )
    p.add_argument(
        "--input-mode",
        type=str,
        default=None,
        metavar="MODE",
        help=(
            "reference_corpus (default): normalize existing policy text; do not invent obligations. "
            "policy_intent_spec: --reference is a guardrails/intent spec; generate in-scope rules from it. "
            "If omitted, default may come from env SCOPE_REWRITER_INPUT_MODE."
        ),
    )
    args = p.parse_args(argv)

    try:
        input_mode_eff = normalize_input_mode(args.input_mode)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    reference = resolve_existing_user_file(
        args.reference, nagv_project_root=args.repo_root / "NagV"
    )
    if not reference.is_file():
        print(f"error: reference not found: {reference}", file=sys.stderr)
        return 2

    work_dir = args.work_dir.resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    max_r = args.max_rounds if args.max_rounds is not None else max_rounds_default()

    try:
        system_instruction = load_scope_rewriter_system_prompt()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    round_idx = 0
    prior_sidecar: dict | None = None
    prior_nl = None

    def one_round(note: str) -> int:
        nonlocal round_idx, prior_sidecar, prior_nl
        if round_idx >= max_r:
            print(f"error: max rounds ({max_r}) reached.", file=sys.stderr)
            return 3
        print(f"\n--- Scope Rewriter round {round_idx} (input_mode={input_mode_eff}) ---\n", flush=True)
        try:
            result = run_scope_rewriter_round(
                reference_path=reference,
                work_dir=work_dir,
                round_index=round_idx,
                prior_nl_path=prior_nl,
                prior_sidecar=prior_sidecar,
                operator_note=note,
                system_instruction=system_instruction,
                input_mode=input_mode_eff,
            )
        except Exception as ex:  # noqa: BLE001
            print(f"error: {ex}", file=sys.stderr)
            return 1

        prior_sidecar = result.record
        prior_nl = result.nl_path
        round_idx += 1

        print(result.parsed.fidelity_summary + "\n", flush=True)
        print(f"strict_equivalence_achievable: {result.parsed.strict_equivalence_achievable}", flush=True)
        print(f"ready_for_wfm: {result.parsed.ready_for_wfm}", flush=True)
        print(f"no_further_agent_changes_recommended: {result.parsed.no_further_agent_changes_recommended}", flush=True)
        if result.parsed.semantic_deltas:
            print("semantic_deltas:", flush=True)
            for d in result.parsed.semantic_deltas:
                print(f"  - {d}", flush=True)
        print(f"\nWrote: {result.nl_path}\nWrote: {result.sidecar_path}\n", flush=True)
        print(
            "Next pivot step (after you accept the text):\n"
            f"  pivot-pipeline --input {result.nl_path} --work-dir <your_pivot_work_dir> ...\n",
            flush=True,
        )
        return 0

    rc = one_round("")
    if rc != 0:
        return rc

    if args.non_interactive:
        return 0

    while True:
        print(
            "[r] Re-run agent on current latest.nl (edit file first, optional note next)\n"
            "[a] Accept — finished (no more agent rounds)\n"
            "[q] Quit without declaring accept\n",
            flush=True,
        )
        choice = input("Choice (r/a/q): ").strip().lower()
        if choice in ("a", "accept"):
            print("Accepted. Use latest.nl as pivot --input when ready.\n", flush=True)
            return 0
        if choice in ("q", "quit"):
            print("Quit.\n", flush=True)
            return 0
        if choice in ("r", "rerun", "re-run"):
            note = input("Operator note (optional, Enter to skip): ").strip()
            rc = one_round(note)
            if rc != 0:
                return rc
            continue
        print("Unknown choice.\n", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
