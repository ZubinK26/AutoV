#!/usr/bin/env python3
"""
Interactive Agent 4 test flow (console UI): no JSONL paths or comment files required.

- Auto-loads the **most recently modified** Gemini JSONL per dataset from test_sets/run_results/:
  wfm_folio_gemini_*.jsonl, wfm_pfolio_gemini_*.jsonl, wfm_stress_gemini_*.jsonl
- Menu lists only examples with OUT_OF_SCOPE in **Agent 3** output (and normal Agent 3 eligibility).
- You work from **Agent 3 text only** on the main screen; disagree indices are **Agent 2
  sub-statement numbers** (the same indices Agent 4 / merge use), as printed on OUT_OF_SCOPE lines.

Does not re-run Agents 1–3 after merge.

  cd <repo-root>
  python test_sets/scripts/run_wfm_agent4_interactive.py
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from wfm_agent4_common import (
    RESULTS_DIR,
    agent3_has_out_of_scope,
    build_user_payload,
    call_agent4_gemini,
    extract_oos_agent2_indices,
    is_eligible,
    load_jsonl,
    parse_numbered_lines,
)

DATASETS: list[tuple[str, str]] = [
    ("F-Gemini", "wfm_folio_gemini_*.jsonl"),
    ("P-FOLIO-Gemini", "wfm_pfolio_gemini_*.jsonl"),
    ("STRESS-Gemini", "wfm_stress_gemini_*.jsonl"),
]


@dataclass
class Pick:
    dataset_label: str
    run_name: str
    run_path: Path
    example_id: str
    difficulty: str
    row: dict


def cls() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def latest_jsonl(results_dir: Path, pattern: str) -> Path | None:
    files = list(results_dir.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def collect_picks(results_dir: Path) -> tuple[list[Pick], list[str]]:
    picks: list[Pick] = []
    notes: list[str] = []
    for label, pat in DATASETS:
        path = latest_jsonl(results_dir, pat)
        if not path:
            notes.append(f"(No file for {label}: {pat} under {results_dir})")
            continue
        try:
            rows = load_jsonl(path)
        except OSError as e:
            notes.append(f"(Could not read {path.name}: {e})")
            continue
        for row in rows:
            if not is_eligible(row):
                continue
            a3 = (row.get("agent_3") or {}).get("output") or ""
            if not agent3_has_out_of_scope(a3):
                continue
            a2 = (row.get("agent_2") or {}).get("output") or ""
            if not extract_oos_agent2_indices(a3, a2):
                ex = row.get("example_id", "?")
                notes.append(
                    f"[skip {ex} in {path.name}: OUT_OF_SCOPE present but no Agent 2 index could be resolved]"
                )
                continue
            picks.append(
                Pick(
                    dataset_label=label,
                    run_name=path.name,
                    run_path=path.resolve(),
                    example_id=str(row.get("example_id", "?")),
                    difficulty=str(row.get("difficulty", "")),
                    row=row,
                )
            )
    return picks, notes


def agent3_line_for_index(agent3: str, idx: int) -> str | None:
    """Agent 3 line that references this Agent 2 sub-statement index, if present."""
    for line in agent3.splitlines():
        s = line.strip()
        if re.match(rf"(?:PASS|REWRITE|OUT_OF_SCOPE):\s*{idx}\.\s", s):
            return line
    return None


def read_nonempty(prompt: str) -> str:
    while True:
        s = input(prompt).strip()
        if s:
            return s
        print("  (non-empty required)")


def confirm_abort() -> bool:
    return input("Type 'yes' to abort and return to the menu: ").strip().lower() == "yes"


def oos_unresolved_lines(agent3: str, agent2: str) -> list[str]:
    """OUT_OF_SCOPE lines that cannot be tied to an Agent 2 sub-statement index."""
    base = parse_numbered_lines(agent2)
    bad: list[str] = []
    for line in agent3.splitlines():
        line_st = line.strip()
        if not line_st.startswith("OUT_OF_SCOPE"):
            continue
        m_num = re.match(r"OUT_OF_SCOPE:\s*(\d+)\.\s*\"", line_st)
        if m_num:
            ix = int(m_num.group(1))
            if ix not in base:
                bad.append(line_st)
            continue
        m_q = re.search(r"OUT_OF_SCOPE:\s*\"((?:[^\"\\\\]|\\\\.)*)\"", line_st)
        if not m_q:
            bad.append(line_st)
            continue
        inner = m_q.group(1).replace(r"\"", '"').replace(r"\\", "\\").strip()
        if not any(inner == t.strip() for t in base.values()):
            bad.append(line_st)
    return bad


def edit_loop(
    *,
    pick: Pick,
    oos: set[int],
    base: dict[int, str],
) -> tuple[dict[int, str], set[int]] | None:
    """
    disagree: index -> comment
    omit: set of indices
    Returns None if user aborts to menu.
    """
    disagree: dict[int, str] = {}
    omit: set[int] = set()

    while True:
        cls()
        print("=== Agent 3 output (read-only) ===\n")
        a3 = (pick.row.get("agent_3") or {}).get("output") or ""
        print(a3)
        print("\n--- Indices reference ---")
        print(
            "Disagree / omit use **Agent 2 sub-statement numbers** (e.g. OUT_OF_SCOPE: 5. \"...\")."
        )
        print(f"OUT_OF_SCOPE indices for this example (must each be disagreed or omitted): {sorted(oos)}")
        print("--- Current choices ---")
        if not disagree and not omit:
            print("(none yet)")
        else:
            for idx in sorted(disagree.keys()):
                print(f"  DISAGREE {idx}: {disagree[idx]!r}")
            for idx in sorted(omit):
                print(f"  OMIT {idx} (user-confirmed drop from bundle)")
        pending = sorted(x for x in oos if x not in disagree and x not in omit)
        if pending:
            print(f"\n** Still required for OUT_OF_SCOPE: {pending} **")
        else:
            print("\nAll OUT_OF_SCOPE lines are covered (disagree or omit).")

        print(
            """
--- Actions ---
  [d] Disagree by number (one index, then one comment)
  [k] Blanket disagree: walk every Agent 2 statement top-to-bottom (comment each)
  [o] Omit confirmed (one Agent 2 index: user accepts dropping that line)
  [u] Undo last disagree / clear one index
  [m] Clear all disagreements
  [x] Abort to menu (confirm)
  [r] Review and send to Agent 4 (only if OOS satisfied and at least one disagree)
"""
        )
        choice = input("Choice: ").strip().lower()

        if choice == "x":
            if confirm_abort():
                return None
            continue

        if choice == "m":
            disagree.clear()
            print("Cleared all disagreements.")
            input("Press Enter...")
            continue

        if choice == "u":
            undo = input("Enter index to remove from disagree (or blank to cancel): ").strip()
            if undo.isdigit():
                k = int(undo)
                disagree.pop(k, None)
                print(f"Removed disagree on {k} if present.")
            rm_omit = input("Enter index to remove from omit (or blank to skip): ").strip()
            if rm_omit.isdigit():
                omit.discard(int(rm_omit))
                print("Removed from omit if present.")
            input("Press Enter...")
            continue

        if choice == "o":
            raw = input("Omit confirmed — Agent 2 index (required to exist): ").strip()
            if not raw.isdigit():
                print("Invalid.")
                input("Press Enter...")
                continue
            idx = int(raw)
            if idx not in base:
                print(f"No Agent 2 statement with index {idx}.")
                input("Press Enter...")
                continue
            if idx in disagree:
                print("Remove that disagree first, or pick another index.")
                input("Press Enter...")
                continue
            if idx not in oos:
                sure = (
                    input(
                        f"Index {idx} is not tagged OUT_OF_SCOPE in Agent 3. Still omit? [y/N]: "
                    )
                    .strip()
                    .lower()
                )
                if sure != "y":
                    continue
            omit.add(idx)
            continue

        if choice == "d":
            raw = input("Agent 2 index to disagree with (one number): ").strip()
            if not raw.isdigit():
                print("Enter a single positive integer.")
                input("Press Enter...")
                continue
            idx = int(raw)
            if idx not in base:
                print(f"No Agent 2 statement with index {idx}.")
                input("Press Enter...")
                continue
            if idx in omit:
                print("That index is marked omit; remove omit first.")
                input("Press Enter...")
                continue
            a3_full = (pick.row.get("agent_3") or {}).get("output") or ""
            ctx = agent3_line_for_index(a3_full, idx)
            print(f"\n--- You are disagreeing with index {idx} ---\n")
            if ctx:
                print(ctx)
                print()
            else:
                print(base[idx])
                print()
            c = read_nonempty("Comment for this line: ")
            disagree[idx] = c
            continue

        if choice == "k":
            print(
                "Blanket disagree: you will comment on every Agent 2 statement in order.\n"
            )
            if input("Replace all existing disagreements with this sweep? [y/N]: ").strip().lower() != "y":
                continue
            disagree.clear()
            for idx in sorted(base.keys()):
                cls()
                print(f"--- Statement {idx} of {sorted(base.keys())} (Agent 2 sub-statement) ---\n")
                a3_full = (pick.row.get("agent_3") or {}).get("output") or ""
                ctx = agent3_line_for_index(a3_full, idx)
                if ctx:
                    print("From Agent 3:\n")
                    print(ctx)
                    print()
                print("Agent 2 wording:\n")
                print(base[idx])
                print()
                if idx in omit:
                    print("(Currently marked OMIT — skipping comment; remove omit first if you disagree.)")
                    input("Press Enter to continue...")
                    continue
                c = read_nonempty(f"Comment for index {idx}: ")
                disagree[idx] = c
            continue

        if choice == "r":
            pending = sorted(x for x in oos if x not in disagree and x not in omit)
            if pending:
                print(f"Cannot review yet — handle OUT_OF_SCOPE indices: {pending}")
                input("Press Enter...")
                continue
            overlap = set(disagree.keys()) & omit
            if overlap:
                print(f"Disagree and omit overlap: {overlap}. Fix first.")
                input("Press Enter...")
                continue
            if not disagree:
                print("Need at least one disagreement to call Agent 4 (current script contract).")
                input("Press Enter...")
                continue
            return disagree, omit

        print("Unknown choice.")
        input("Press Enter...")


def review_and_send(
    pick: Pick,
    disagree: dict[int, str],
    omit: set[int],
) -> None:
    cls()
    print("=== Review ===\n")
    d_list = sorted(disagree.keys())
    for idx in d_list:
        print(f"  DISAGREE {idx}: {disagree[idx]!r}")
    for idx in sorted(omit):
        print(f"  OMIT {idx}")
    print()
    if input("Send to Agent 4? [y/N]: ").strip().lower() != "y":
        return
    mp = input("Show merge preview after response? [Y/n]: ").strip().lower() != "n"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    default_out = RESULTS_DIR / f"wfm_agent4_interactive_{pick.example_id}_{stamp}.md"
    raw_out = input(f"Save report to [{default_out}]: ").strip()
    out_path = Path(raw_out) if raw_out else default_out

    comments = [disagree[i] for i in d_list]
    try:
        payload = build_user_payload(
            row=pick.row,
            run_path=pick.run_path,
            disagree=d_list,
            comments=comments,
            omit_confirmed=sorted(omit),
        )
    except ValueError as e:
        print(f"ERROR: {e}")
        input("Press Enter...")
        return

    call_agent4_gemini(
        user_payload=payload,
        row=pick.row,
        run_path=pick.run_path,
        ex_id=pick.example_id,
        merge_preview=mp,
        disagree=d_list,
        omit_confirmed=sorted(omit),
        out=out_path,
    )
    input("\nPress Enter to return to menu...")


def main() -> int:
    print(
        "Agent 4 interactive (Gemini). Loads latest FOLIO / P-FOLIO / STRESS Gemini JSONL files automatically.\n"
        "Examples shown: Agent 3 completed, OUT_OF_SCOPE present, OOS mappable to Agent 2 indices.\n"
    )
    picks, notes = collect_picks(RESULTS_DIR)
    for n in notes:
        print(n)
    if not picks:
        print("\nNo matching examples. Run Gemini Agents 1–3 first; check test_sets/run_results/.")
        return 1

    while True:
        cls()
        print("=== Pick an example (OUT_OF_SCOPE in Agent 3) ===\n")
        for i, p in enumerate(picks, start=1):
            short = p.difficulty[:56] + "..." if len(p.difficulty) > 59 else p.difficulty
            print(f"  [{i:2}] {p.example_id:<6}  {p.dataset_label:<16}  {p.run_name}")
            print(f"       {short}")
            print()
        print("  [q] Quit")
        sel = input("Number: ").strip().lower()
        if sel == "q":
            return 0
        if not sel.isdigit():
            continue
        n = int(sel)
        if not 1 <= n <= len(picks):
            continue
        pick = picks[n - 1]
        a2 = (pick.row.get("agent_2") or {}).get("output") or ""
        a3 = (pick.row.get("agent_3") or {}).get("output") or ""
        bad = oos_unresolved_lines(a3, a2)
        if bad:
            cls()
            print("This example has OUT_OF_SCOPE lines that could not be matched to Agent 2 text.")
            print("Use the CLI harness with --run-jsonl or fix run artifacts.\n")
            for ln in bad[:5]:
                print(ln[:200])
            input("\nPress Enter...")
            continue
        oos = extract_oos_agent2_indices(a3, a2)
        base = parse_numbered_lines(a2)
        if not base:
            print("Could not parse Agent 2 numbered lines; skipping.")
            input("Press Enter...")
            continue
        result = edit_loop(pick=pick, oos=oos, base=base)
        if result is None:
            continue
        d, o = result
        review_and_send(pick, d, o)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
