#!/usr/bin/env python3
"""
Run FOLIO-only examples from wfm_folio_pffolio_examples_en.md through Agents 1→2→3
via Anthropic Claude (contract-frozen defaults). Agent 4 is skipped.

Usage (from repo root that contains asp/wfm/ and test_sets/):
  pip install -r test_sets/requirements-wfm-test.txt
  copy .env.example .env   # then edit .env — never commit .env
  python test_sets/scripts/run_wfm_folio_claude.py

API key: load from .env (ANTHROPIC_API_KEY) or environment. See .gitignore.

Optional:
  python test_sets/scripts/run_wfm_folio_claude.py --dry-run
  python test_sets/scripts/run_wfm_folio_claude.py --stress   # edge/reject harness; wfm_stress_gemini-style outputs as wfm_stress_claude_*
  python test_sets/scripts/run_wfm_folio_claude.py --clincon  # ClinCon fragment smoke (C-*); wfm_clincon_claude_*
  ANTHROPIC_MODEL=claude-3-5-sonnet-20241022 python ...
  ANTHROPIC_THINKING_BUDGET_TOKENS=0 python ...   # disable extended thinking (use temperature)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# --- paths ---
SCRIPT_DIR = Path(__file__).resolve().parent
TEST_SETS = SCRIPT_DIR.parent
REPO_ROOT = TEST_SETS.parent  # directory containing asp/wfm/ and test_sets/
WFM_DIR = REPO_ROOT / "asp" / "wfm"
PROMPTS_DIR = WFM_DIR / "prompts"
EXAMPLES_FILE = TEST_SETS / "wfm_folio_pffolio_examples_en.md"
STRESS_EXAMPLES_FILE = TEST_SETS / "wfm_stress_examples_en.md"
CLINCON_EXAMPLES_FILE = TEST_SETS / "wfm_clincon_fragment_examples_en.md"
CONFIG_FILE = WFM_DIR / "config" / "wfm.json"
RESULTS_DIR = TEST_SETS / "run_results"

# --- frozen defaults (see wfm_api_contract_frozen.md) ---
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 16384
# Extended thinking: API requires budget_tokens >= 1024 and < max_tokens; incompatible with temperature != default.
DEFAULT_THINKING_BUDGET_TOKENS = 10000


def load_repo_dotenv() -> None:
    """Load REPO_ROOT/.env into os.environ if python-dotenv and file exist."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


@dataclass
class Example:
    ex_id: str
    difficulty: str
    text: str


def extract_system_prompt(md_path: Path) -> str:
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"```\n(.*?)```", raw, re.DOTALL)
    if not m:
        raise ValueError(f"No ``` fenced system block in {md_path}")
    return m.group(1).strip()


def load_wfm_config() -> dict:
    if not CONFIG_FILE.is_file():
        return {"compound_operator_limit": 8}
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def inject_compound_limit(agent2_system: str, limit: int) -> str:
    """Sync Agent 2 prompt numbers with wfm.json."""
    s = agent2_system
    s = re.sub(r"COMPOUND OPERATOR LIMIT:\s*\d+", f"COMPOUND OPERATOR LIMIT: {limit}", s)
    s = re.sub(r"\*\*at most \d+\*\*", f"**at most {limit}**", s)
    s = re.sub(r"at most \d+ operators", f"at most {limit} operators", s)
    s = re.sub(r"OPERATOR_BUDGET:\s*\d+", f"OPERATOR_BUDGET: {limit}", s)
    s = re.sub(r"still exceeds \d+", f"still exceeds {limit}", s)
    s = re.sub(r"has at most \d+ operators", f"has at most {limit} operators", s)
    return s


def parse_folio_examples(path: Path) -> list[Example]:
    text = path.read_text(encoding="utf-8")
    m = re.search(
        r"## FOLIO.*?\n\n(.*?)---\s*\n\n## P-FOLIO",
        text,
        re.DOTALL,
    )
    if not m:
        raise ValueError(f"Could not find FOLIO section in {path}")
    section = m.group(1)
    out: list[Example] = []
    for block in re.finditer(
        r"^### (F-\d+) \(([^)]+)\)\s*\n\n(.+?)(?=^### |\Z)",
        section,
        re.MULTILINE | re.DOTALL,
    ):
        out.append(
            Example(
                ex_id=block.group(1),
                difficulty=block.group(2),
                text=block.group(3).strip(),
            )
        )
    if not out:
        raise ValueError("No F-* examples parsed")
    return out


def _parse_example_blocks(section: str, block_pattern: str, label: str) -> list[Example]:
    out: list[Example] = []
    for block in re.finditer(block_pattern, section, re.MULTILINE | re.DOTALL):
        out.append(
            Example(
                ex_id=block.group(1),
                difficulty=block.group(2),
                text=block.group(3).strip(),
            )
        )
    if not out:
        raise ValueError(f"No {label} examples parsed")
    return out


def parse_stress_examples(path: Path) -> list[Example]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## STRESS\s*\n\n(.*)\Z", text, re.DOTALL)
    if not m:
        raise ValueError(f"Could not find ## STRESS section in {path}")
    section = m.group(1).strip()
    return _parse_example_blocks(
        section,
        r"^### ((?:R|E)-\d+) \(([^)]+)\)\s*\n\n(.+?)(?=^### |\Z)",
        "R-* / E-*",
    )


def parse_clincon_examples(path: Path) -> list[Example]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## CLINCON\s*\n\n(.*)\Z", text, re.DOTALL)
    if not m:
        raise ValueError(f"Could not find ## CLINCON section in {path}")
    section = m.group(1).strip()
    return _parse_example_blocks(
        section,
        r"^### (C-\d+) \(([^)]+)\)\s*\n\n(.+?)(?=^### |\Z)",
        "C-*",
    )


def call_claude(
    client: object,
    *,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    thinking_budget_tokens: int | None,
) -> tuple[str, dict]:
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    # With extended thinking enabled, do not pass temperature/top_k (API constraint).
    if thinking_budget_tokens is not None:
        kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": thinking_budget_tokens,
        }
    else:
        kwargs["temperature"] = temperature

    msg = client.messages.create(**kwargs)
    text_blocks = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
    assistant_text = "".join(text_blocks)
    usage = {
        "input_tokens": getattr(msg.usage, "input_tokens", None),
        "output_tokens": getattr(msg.usage, "output_tokens", None),
    }
    return assistant_text, usage


def limit_exceeded(agent2_output: str) -> bool:
    return bool(re.search(r"LIMIT_EXCEEDED\s*:\s*true", agent2_output, re.I))


def main() -> int:
    parser = argparse.ArgumentParser(description="WFM Agents 1–3 API smoke (FOLIO, stress, or ClinCon harness).")
    parser.add_argument("--dry-run", action="store_true", help="Parse prompts/examples only; no API.")
    mx = parser.add_mutually_exclusive_group()
    mx.add_argument(
        "--stress",
        action="store_true",
        help="Use ## STRESS (R-* / E-*) from wfm_stress_examples_en.md by default; writes wfm_stress_claude_*.",
    )
    mx.add_argument(
        "--clincon",
        action="store_true",
        help="Use ## CLINCON (C-*) from wfm_clincon_fragment_examples_en.md by default; writes wfm_clincon_claude_*.",
    )
    parser.add_argument(
        "--examples",
        type=Path,
        default=EXAMPLES_FILE,
        help="Markdown: FOLIO+P-FOLIO default, or stress/ClinCon file when using --stress / --clincon.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=RESULTS_DIR,
        help="Directory for report + jsonl",
    )
    args = parser.parse_args()

    load_repo_dotenv()

    cfg = load_wfm_config()
    lim = int(cfg.get("compound_operator_limit", 8))

    p1 = extract_system_prompt(PROMPTS_DIR / "agent_1_completeness_ambiguity.md")
    p2 = inject_compound_limit(
        extract_system_prompt(PROMPTS_DIR / "agent_2_decomposition.md"),
        lim,
    )
    p3 = extract_system_prompt(PROMPTS_DIR / "agent_3_scope_rewrite.md")

    if args.stress:
        stress_path = args.examples if args.examples != EXAMPLES_FILE else STRESS_EXAMPLES_FILE
        examples = parse_stress_examples(stress_path)
        examples_file_resolved = str(stress_path.resolve())
        example_set = "stress"
        out_prefix = "wfm_stress_claude"
        report_heading = "# WFM automated run — stress harness (R-* / E-*), Agents 1 → 2 → 3"
    elif args.clincon:
        clincon_path = args.examples if args.examples != EXAMPLES_FILE else CLINCON_EXAMPLES_FILE
        examples = parse_clincon_examples(clincon_path)
        examples_file_resolved = str(clincon_path.resolve())
        example_set = "clincon"
        out_prefix = "wfm_clincon_claude"
        report_heading = "# WFM automated run — ClinCon fragment smoke (C-*), Agents 1 → 2 → 3"
    else:
        examples = parse_folio_examples(args.examples)
        examples_file_resolved = str(args.examples.resolve())
        example_set = "folio"
        out_prefix = "wfm_folio_run"
        report_heading = "# WFM automated run — FOLIO examples (Agents 1 → 2 → 3)"

    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL).strip()
    temperature = float(os.environ.get("ANTHROPIC_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    max_tokens = int(os.environ.get("ANTHROPIC_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))

    thinking_raw = os.environ.get("ANTHROPIC_THINKING_BUDGET_TOKENS", "").strip()
    thinking_budget: int | None
    if thinking_raw == "":
        thinking_budget = DEFAULT_THINKING_BUDGET_TOKENS
    else:
        thinking_budget = int(thinking_raw) or None
    if thinking_budget is not None:
        thinking_budget = max(1024, min(thinking_budget, max_tokens - 1))

    contract_info = {
        "example_set": example_set,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "thinking_budget_tokens": thinking_budget,
        "compound_operator_limit": lim,
        "examples_file": examples_file_resolved,
        "prompt_files": {
            "agent_1": str(PROMPTS_DIR / "agent_1_completeness_ambiguity.md"),
            "agent_2": str(PROMPTS_DIR / "agent_2_decomposition.md"),
            "agent_3": str(PROMPTS_DIR / "agent_3_scope_rewrite.md"),
        },
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    report_path = args.out_dir / f"{out_prefix}_{stamp}.md"
    jsonl_path = args.out_dir / f"{out_prefix}_{stamp}.jsonl"

    if args.dry_run:
        thinking_raw = os.environ.get("ANTHROPIC_THINKING_BUDGET_TOKENS", "").strip()
        tb = (
            DEFAULT_THINKING_BUDGET_TOKENS
            if thinking_raw == ""
            else int(thinking_raw) or None
        )
        label = (
            "STRESS (R-* / E-*)"
            if args.stress
            else "CLINCON (C-*)"
            if args.clincon
            else "FOLIO"
        )
        print("Dry run OK — parsed", len(examples), f"{label} examples.")
        for e in examples:
            print(f"  {e.ex_id} ({e.difficulty}) {len(e.text)} chars")
        print("Compound limit injected:", lim)
        print("Extended thinking budget tokens:", tb)
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        print(
            "ERROR: Set ANTHROPIC_API_KEY in "
            f"{REPO_ROOT / '.env'} (see .env.example) or in the environment.",
            file=sys.stderr,
        )
        return 2

    try:
        import anthropic
    except ImportError:
        print("ERROR: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    client = anthropic.Anthropic(api_key=api_key)

    if example_set == "stress":
        set_bullet = "- **Example set:** `stress` (`test_sets/wfm_stress_examples_en.md`, ## STRESS)"
    elif example_set == "clincon":
        set_bullet = "- **Example set:** `clincon` (`test_sets/wfm_clincon_fragment_examples_en.md`, ## CLINCON)"
    else:
        set_bullet = "- **Example set:** `folio` (F-* blocks)"
    report_lines: list[str] = [
        report_heading,
        "",
        f"**UTC timestamp:** {stamp}",
        "",
        "## Frozen contract (this run)",
        "",
        set_bullet,
        f"- **Model:** `{model}`",
        f"- **Temperature:** `{temperature}`"
        + (
            " *(omitted when extended thinking is on — API requirement)*"
            if thinking_budget is not None
            else ""
        ),
        f"- **Max output tokens:** `{max_tokens}`",
        f"- **Extended thinking budget (tokens):** `{thinking_budget}`"
        if thinking_budget is not None
        else "- **Extended thinking:** off (`ANTHROPIC_THINKING_BUDGET_TOKENS=0`)",
        f"- **Compound operator limit (injected):** `{lim}`",
        "- **Agent 4:** skipped (no user disagreement simulation)",
        "",
        "Full table: `test_sets/wfm_api_contract_frozen.md`",
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
                "agent_1": {},
                "agent_2": {},
                "agent_3": {},
            }

            report_lines.append(f"## {ex.ex_id} ({ex.difficulty})")
            report_lines.append("")
            report_lines.append("### Input")
            report_lines.append("")
            report_lines.append(ex.text)
            report_lines.append("")

            a1_text, u1 = call_claude(
                client,
                model=model,
                system=p1,
                user=ex.text,
                temperature=temperature,
                max_tokens=max_tokens,
                thinking_budget_tokens=thinking_budget,
            )
            row["agent_1"] = {"output": a1_text, "usage": u1}

            report_lines.append("### Agent 1")
            report_lines.append("")
            report_lines.append(a1_text)
            report_lines.append("")

            a2_text, u2 = call_claude(
                client,
                model=model,
                system=p2,
                user=a1_text,
                temperature=temperature,
                max_tokens=max_tokens,
                thinking_budget_tokens=thinking_budget,
            )
            row["agent_2"] = {"output": a2_text, "usage": u2}

            report_lines.append("### Agent 2")
            report_lines.append("")
            report_lines.append(a2_text)
            report_lines.append("")

            if limit_exceeded(a2_text):
                row["agent_3"] = {
                    "skipped": True,
                    "reason": "Agent 2 emitted LIMIT_EXCEEDED — pipeline would terminate before Agent 3 per WFM.",
                }
                report_lines.append("### Agent 3")
                report_lines.append("")
                report_lines.append(
                    "*SKIPPED — Agent 2 returned LIMIT_EXCEEDED (WFM would reset to user input).*"
                )
                report_lines.append("")
            else:
                a3_text, u3 = call_claude(
                    client,
                    model=model,
                    system=p3,
                    user=a2_text,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    thinking_budget_tokens=thinking_budget,
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
