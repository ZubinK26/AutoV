#!/usr/bin/env python3
"""
Run Agent 4 (Gemini only) from a prior WFM JSONL run: pick one eligible example by id (F-#, PF-#, R-#, E-#, …),
build the structured disagreement payload, call the model, optionally preview Style A merge.

Prereq: JSONL from run_wfm_folio_gemini.py (--stress / default FOLIO / --pfolio).

For a menu-driven flow (latest FOLIO / P-FOLIO / STRESS Gemini JSONL, OUT_OF_SCOPE examples only), use:
  python test_sets/scripts/run_wfm_agent4_interactive.py

See test_sets/wfm_api_contract_gemini.md, test_sets/README.md, asp/wfm/prompts/agent_4_user_interaction.md.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wfm_agent4_common import (
    build_user_payload,
    call_agent4_gemini,
    is_eligible,
    load_jsonl,
)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agent 4 from prior WFM JSONL run (pick F-#/R-#/… by id)."
    )
    parser.add_argument(
        "--run-jsonl",
        type=Path,
        required=True,
        help="Path to wfm_*_<UTC>.jsonl from a prior Agents 1–3 run.",
    )
    parser.add_argument(
        "--list-eligible",
        action="store_true",
        help="Print menu of example ids in this file that reached Agent 3 (then exit).",
    )
    parser.add_argument(
        "--example",
        type=str,
        default=None,
        help="Example id to run, e.g. F-4, PF-2, R-1, E-3 (must appear in --run-jsonl).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload only; do not call Gemini.",
    )
    parser.add_argument(
        "--disagree",
        type=str,
        default="",
        help="Comma-separated 1-based line indices the user disagreed with (e.g. 6,8).",
    )
    parser.add_argument(
        "--comments-file",
        type=Path,
        default=None,
        help="Text file: one comment line per disagreed index (same order as --disagree).",
    )
    parser.add_argument(
        "--omit-confirmed",
        type=str,
        default="",
        help="Comma-separated indices user confirmed to omit from bundle (optional).",
    )
    parser.add_argument(
        "--merge-preview",
        action="store_true",
        help="After API response, parse wfm_patch and print Style A merged NL (best-effort).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write Markdown report (payload + response) under test_sets/run_results/.",
    )
    ns = parser.parse_args()

    path = ns.run_jsonl.resolve()
    if not path.is_file():
        print(f"ERROR: not a file: {path}", file=sys.stderr)
        return 2

    rows = load_jsonl(path)
    by_id = {r.get("example_id"): r for r in rows}

    if ns.list_eligible:
        print(f"Eligible examples (Agent 3 completed, no LIMIT_EXCEEDED): {path.name}")
        print(f"{'ID':<8}  {'Difficulty / note'}")
        for r in rows:
            if not is_eligible(r):
                continue
            eid = r.get("example_id", "?")
            diff = r.get("difficulty", "")
            oos = (
                "has OUT_OF_SCOPE"
                if "OUT_OF_SCOPE" in (r.get("agent_3") or {}).get("output", "")
                else ""
            )
            tail = f"  [{oos}]" if oos else ""
            print(f"{eid:<8}  {diff}{tail}")
        print(
            "\nPick one and pass:  --example <ID>  plus --disagree / --comments-file / --omit-confirmed as needed."
        )
        print("Or run: python test_sets/scripts/run_wfm_agent4_interactive.py")
        return 0

    if not ns.example:
        print("ERROR: pass --example <ID> or use --list-eligible.", file=sys.stderr)
        return 2

    ex_id = ns.example.strip()
    if ex_id not in by_id:
        print(f"ERROR: no row with example_id {ex_id!r} in {path}", file=sys.stderr)
        return 2

    row = by_id[ex_id]
    if not is_eligible(row):
        print(
            f"ERROR: {ex_id} is not eligible (LIMIT_EXCEEDED or Agent 3 skipped). Use --list-eligible.",
            file=sys.stderr,
        )
        return 2

    disagree = [int(x.strip()) for x in ns.disagree.split(",") if x.strip()]
    omit_confirmed = [int(x.strip()) for x in ns.omit_confirmed.split(",") if x.strip()]
    comments: list[str] = []
    if disagree:
        if not ns.comments_file or not ns.comments_file.is_file():
            print("ERROR: --comments-file required when --disagree is non-empty.", file=sys.stderr)
            return 2
        raw_lines = ns.comments_file.read_text(encoding="utf-8").splitlines()
        non_empty = [ln.strip() for ln in raw_lines if ln.strip()]
        if len(non_empty) != len(disagree):
            print(
                f"ERROR: comments file must have exactly {len(disagree)} non-empty lines "
                f"(one per disagreed index); got {len(non_empty)}.",
                file=sys.stderr,
            )
            return 2
        comments = non_empty

    try:
        user_payload = build_user_payload(
            row=row,
            run_path=path,
            disagree=disagree,
            comments=comments,
            omit_confirmed=omit_confirmed,
        )
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if ns.dry_run:
        print(user_payload)
        return 0

    if not disagree:
        print(
            "ERROR: pass at least one index in --disagree (with --comments-file), "
            "or use --dry-run to print the confirmation payload only.",
            file=sys.stderr,
        )
        return 2

    return call_agent4_gemini(
        user_payload=user_payload,
        row=row,
        run_path=path,
        ex_id=ex_id,
        merge_preview=ns.merge_preview,
        disagree=disagree,
        omit_confirmed=omit_confirmed,
        out=ns.out,
    )


if __name__ == "__main__":
    raise SystemExit(main())
