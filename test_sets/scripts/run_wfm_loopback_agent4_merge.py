#!/usr/bin/env python3
"""
Run Agents 1→2→3 (Gemini) on the **Style A merge preview** text saved in Agent 4 interactive
(or compatible) Markdown reports — loop-back smoke test after confirmation.

Extracts, per report:
  - **Example id** from `**Example:** `R-1``
  - **Difficulty** from `- **difficulty:**` inside the Payload block (fallback: loopback placeholder)
  - **Input NL** = body under `--- Style A merge preview ... ---` (numbered lines)

Usage (repo root):
  python test_sets/scripts/run_wfm_loopback_agent4_merge.py \\
    test_sets/run_results/wfm_agent4_interactive_R-1_20260405_160649Z.md \\
    test_sets/run_results/wfm_agent4_interactive_R-2_20260405_160011Z.md \\
    test_sets/run_results/wfm_agent4_interactive_E-3_20260405_120628Z.md

  # Or glob (quoted in PowerShell):
  python test_sets/scripts/run_wfm_loopback_agent4_merge.py --glob "test_sets/run_results/wfm_agent4_interactive_*.md"

  python test_sets/scripts/run_wfm_loopback_agent4_merge.py --dry-run --glob "..."
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_wfm_folio_gemini import (  # noqa: E402
    RESULTS_DIR,
    REPO_ROOT,
    WFM_DIR,
    PROMPTS_DIR,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_OUTPUT_TOKENS,
    load_repo_dotenv,
    load_wfm_config,
    extract_system_prompt,
    inject_compound_limit,
    call_gemini,
    limit_exceeded,
    env_thinking_level,
)


@dataclass
class LoopbackExample:
    ex_id: str
    difficulty: str
    text: str
    source_report: Path


def _extract_payload_fence(md: str) -> str | None:
    m = re.search(
        r"## Payload\s*\n+```\s*\n(.*?)```",
        md,
        re.DOTALL | re.IGNORECASE,
    )
    return m.group(1).strip() if m else None


def parse_agent4_report(path: Path) -> LoopbackExample:
    raw = path.read_text(encoding="utf-8")
    ex_m = re.search(r"\*\*Example:\*\*\s*`([^`]+)`", raw)
    if not ex_m:
        raise ValueError(f"{path}: missing **Example:** `ID`")
    ex_id = ex_m.group(1).strip()

    difficulty = "loopback · Agent 4 merge preview"
    pay = _extract_payload_fence(raw)
    if pay:
        d_m = re.search(r"^-\s*\*\*difficulty:\*\*\s*(.+)$", pay, re.MULTILINE)
        if d_m:
            difficulty = d_m.group(1).strip()

    prev_m = re.search(
        r"---\s*Style A merge preview[^\n]*---\s*\n+([\s\S]*?)(?=\n\s*\(Merge base:|\n\n---|\Z)",
        raw,
    )
    if not prev_m:
        raise ValueError(
            f"{path}: no '--- Style A merge preview ---' block found "
            "(re-run Agent 4 with merge preview enabled)"
        )
    body = prev_m.group(1).strip()
    if not body:
        raise ValueError(f"{path}: empty merge preview body")
    return LoopbackExample(
        ex_id=ex_id,
        difficulty=difficulty,
        text=body,
        source_report=path.resolve(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Agents 1→3 on Style A merge text from Agent 4 interactive Markdown reports.",
    )
    parser.add_argument(
        "reports",
        nargs="*",
        type=Path,
        help="Paths to wfm_agent4_interactive_*.md (optional if --glob is set).",
    )
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help="Glob for report paths, e.g. test_sets/run_results/wfm_agent4_interactive_*.md "
        "(merged with positional paths).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse only; no API.")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Directory for report + jsonl",
    )
    ns = parser.parse_args()

    paths: list[Path] = []
    for p in ns.reports:
        paths.append(p)
    if ns.glob:
        paths.extend(Path(p) for p in glob.glob(ns.glob, recursive=False))
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)

    if not uniq:
        print(
            "ERROR: pass at least one report path or use --glob.",
            file=sys.stderr,
        )
        return 2

    examples: list[LoopbackExample] = []
    for p in sorted(uniq, key=lambda x: str(x)):
        if not p.is_file():
            print(f"ERROR: not a file: {p}", file=sys.stderr)
            return 2
        try:
            examples.append(parse_agent4_report(p))
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2

    load_repo_dotenv()
    cfg = load_wfm_config()
    lim = int(cfg.get("compound_operator_limit", 8))

    if ns.dry_run:
        print("Dry run OK —", len(examples), "merge previews parsed.")
        for e in examples:
            print(f"  {e.ex_id} ({e.difficulty}) <- {e.source_report.name}")
            print(f"    input lines: {len(e.text.splitlines())}, chars: {len(e.text)}")
        return 0

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip()
    temperature = float(os.environ.get("GEMINI_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS)))
    thinking_level = env_thinking_level()

    contract_info = {
        "provider": "google_genai",
        "example_set": "agent4_merge_loopback",
        "model": model,
        "temperature": temperature,
        "max_output_tokens": max_out,
        "thinking_level": (
            thinking_level.value if thinking_level is not None else "omitted_api_default"
        ),
        "compound_operator_limit": lim,
        "examples_file": "; ".join(str(e.source_report) for e in examples),
        "prompt_files": {
            "agent_1": str(PROMPTS_DIR / "agent_1_completeness_ambiguity.md"),
            "agent_2": str(PROMPTS_DIR / "agent_2_decomposition.md"),
            "agent_3": str(PROMPTS_DIR / "agent_3_scope_rewrite.md"),
        },
    }

    p1 = extract_system_prompt(PROMPTS_DIR / "agent_1_completeness_ambiguity.md")
    p2 = inject_compound_limit(
        extract_system_prompt(PROMPTS_DIR / "agent_2_decomposition.md"),
        lim,
    )
    p3 = extract_system_prompt(PROMPTS_DIR / "agent_3_scope_rewrite.md")

    ns.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    out_prefix = "wfm_agent4_merge_loopback_gemini"
    report_path = ns.out_dir / f"{out_prefix}_{stamp}.md"
    jsonl_path = ns.out_dir / f"{out_prefix}_{stamp}.jsonl"

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(
            f"ERROR: Set GEMINI_API_KEY in {REPO_ROOT / '.env'} (see .env.example).",
            file=sys.stderr,
        )
        return 2

    try:
        from google import genai
    except ImportError:
        print("ERROR: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    client = genai.Client(api_key=api_key)

    report_lines: list[str] = [
        "# WFM loopback — Agent 4 merge preview → Agents 1 → 2 → 3 (Gemini)",
        "",
        f"**UTC timestamp:** {stamp}",
        "",
        "## Contract (this run)",
        "",
        "- **Example set:** `agent4_merge_loopback` (Style A text from Agent 4 reports)",
        f"- **Model:** `{model}`",
        f"- **Temperature:** `{temperature}`",
        f"- **Max output tokens:** `{max_out}`",
        "- **Source reports:** see each row `contract.examples_file` / per-example source below",
        "",
        "---",
        "",
    ]

    with jsonl_path.open("w", encoding="utf-8") as jf:
        for ex in examples:
            row: dict = {
                "example_id": ex.ex_id,
                "difficulty": ex.difficulty,
                "contract": contract_info,
                "loopback_source_report": str(ex.source_report),
                "agent_1": {},
                "agent_2": {},
                "agent_3": {},
            }

            report_lines.append(f"## {ex.ex_id} ({ex.difficulty})")
            report_lines.append("")
            report_lines.append(f"### Source Agent 4 report\n\n`{ex.source_report.as_posix()}`\n")
            report_lines.append("### Input (merge preview)")
            report_lines.append("")
            report_lines.append(ex.text)
            report_lines.append("")

            a1_text, u1 = call_gemini(
                client,
                model=model,
                system=p1,
                user=ex.text,
                temperature=temperature,
                max_output_tokens=max_out,
                thinking_level=thinking_level,
            )
            row["agent_1"] = {"output": a1_text, "usage": u1}
            report_lines.append("### Agent 1")
            report_lines.append("")
            report_lines.append(a1_text)
            report_lines.append("")

            a2_text, u2 = call_gemini(
                client,
                model=model,
                system=p2,
                user=a1_text,
                temperature=temperature,
                max_output_tokens=max_out,
                thinking_level=thinking_level,
            )
            row["agent_2"] = {"output": a2_text, "usage": u2}
            report_lines.append("### Agent 2")
            report_lines.append("")
            report_lines.append(a2_text)
            report_lines.append("")

            if limit_exceeded(a2_text):
                row["agent_3"] = {
                    "skipped": True,
                    "reason": "Agent 2 emitted LIMIT_EXCEEDED",
                }
                report_lines.append("### Agent 3")
                report_lines.append("")
                report_lines.append("*SKIPPED — LIMIT_EXCEEDED*")
                report_lines.append("")
            else:
                a3_text, u3 = call_gemini(
                    client,
                    model=model,
                    system=p3,
                    user=a2_text,
                    temperature=temperature,
                    max_output_tokens=max_out,
                    thinking_level=thinking_level,
                )
                row["agent_3"] = {"output": a3_text, "usage": u3}
                report_lines.append("### Agent 3")
                report_lines.append("")
                report_lines.append(a3_text)
                report_lines.append("")

            report_lines.append("---")
            report_lines.append("")
            jf.write(json.dumps(row, ensure_ascii=False) + "\n")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print("Wrote:", report_path)
    print("Wrote:", jsonl_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
