#!/usr/bin/env python3
"""
Run FOLIO or P-FOLIO–section examples from wfm_folio_pffolio_examples_en.md through Agents 1→2→3
via Google Gemini API (contract aligned with wfm_api_contract_gemini.md). Agent 4 is skipped.

Usage (from repo root that contains asp/wfm/ and test_sets/):
  pip install -r test_sets/requirements-wfm-test.txt
  copy .env.example .env   # then set GEMINI_API_KEY; never commit .env
  python test_sets/scripts/run_wfm_folio_gemini.py
  python test_sets/scripts/run_wfm_folio_gemini.py --pfolio   # P-FOLIO base text (PF-*); separate output files
  python test_sets/scripts/run_wfm_folio_gemini.py --stress  # edge/reject harness (R-* / E-*); wfm_stress_examples_en.md
  python test_sets/scripts/run_wfm_folio_gemini.py --clincon  # ClinCon fragment smoke (C-*); wfm_clincon_fragment_examples_en.md

Optional:
  python test_sets/scripts/run_wfm_folio_gemini.py --dry-run
  python test_sets/scripts/run_wfm_folio_gemini.py --pfolio --dry-run
  python test_sets/scripts/run_wfm_folio_gemini.py --stress --dry-run
  python test_sets/scripts/run_wfm_folio_gemini.py --clincon --dry-run
  GEMINI_MODEL=gemini-3.1-pro-preview python ...
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
REPO_ROOT = TEST_SETS.parent
WFM_DIR = REPO_ROOT / "asp" / "wfm"
PROMPTS_DIR = WFM_DIR / "prompts"
EXAMPLES_FILE = TEST_SETS / "wfm_folio_pffolio_examples_en.md"
STRESS_EXAMPLES_FILE = TEST_SETS / "wfm_stress_examples_en.md"
CLINCON_EXAMPLES_FILE = TEST_SETS / "wfm_clincon_fragment_examples_en.md"
CONFIG_FILE = WFM_DIR / "config" / "wfm.json"
RESULTS_DIR = TEST_SETS / "run_results"

# --- defaults (see test_sets/wfm_api_contract_gemini.md) ---
DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_OUTPUT_TOKENS = 16384


def load_repo_dotenv() -> None:
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
    return _parse_example_blocks(
        section, r"^### (F-\d+) \(([^)]+)\)\s*\n\n(.+?)(?=^### |\Z)", "F-*"
    )


def parse_pfolio_examples(path: Path) -> list[Example]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"## P-FOLIO.*?\n\n(.*)\Z", text, re.DOTALL)
    if not m:
        raise ValueError(f"Could not find P-FOLIO section in {path}")
    section = m.group(1).strip()
    return _parse_example_blocks(
        section, r"^### (PF-\d+) \(([^)]+)\)\s*\n\n(.+?)(?=^### |\Z)", "PF-*"
    )


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


def model_supports_thinking_config(model: str) -> bool:
    """
    Whether to send ``ThinkingConfig`` for ``generate_content``.

    Gemini 3.x (e.g. ``gemini-3-flash-preview``, ``gemini-3.1-pro-preview``) supports
    ``thinking_level``; ``gemini-2.5-pro`` does not (omit config).

    Some models return 400 ``Thinking level is not supported for this model`` if
    ``thinking_config`` is set. Override: ``GEMINI_FORCE_NO_THINKING=1`` (omit always),
    ``GEMINI_FORCE_THINKING_CONFIG=1`` (send when ``thinking_level`` is set).
    """
    m = (model or "").strip().lower()
    if os.environ.get("GEMINI_FORCE_NO_THINKING", "").strip().lower() in ("1", "true", "yes"):
        return False
    if os.environ.get("GEMINI_FORCE_THINKING_CONFIG", "").strip().lower() in ("1", "true", "yes"):
        return True
    if m.startswith("gemini-2.5-pro"):
        return False
    return True


def env_thinking_level():
    """Parse GEMINI_THINKING_LEVEL; see wfm_api_contract_gemini.md."""
    from google.genai import types as genai_types

    raw = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower()
    if raw in ("", "low"):
        return genai_types.ThinkingLevel.LOW
    if raw == "medium":
        return genai_types.ThinkingLevel.MEDIUM
    if raw == "high":
        return genai_types.ThinkingLevel.HIGH
    if raw == "minimal":
        return genai_types.ThinkingLevel.MINIMAL
    if raw in ("unspecified", "api_default", "default"):
        return None  # omit ThinkingConfig → Gemini 3 defaults (high)
    print(
        f"WARNING: Unknown GEMINI_THINKING_LEVEL={raw!r}; using LOW.",
        file=sys.stderr,
    )
    return genai_types.ThinkingLevel.LOW


def call_gemini(
    client: object,
    *,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_output_tokens: int,
    thinking_level,
) -> tuple[str, dict]:
    from google.genai import types as genai_types

    cfg_kwargs: dict = {
        "system_instruction": system,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if thinking_level is not None and model_supports_thinking_config(model):
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(
            thinking_level=thinking_level,
        )

    response = client.models.generate_content(
        model=model,
        contents=user,
        config=genai_types.GenerateContentConfig(**cfg_kwargs),
    )
    assistant_text = (response.text or "").strip()
    usage: dict = {"input_tokens": None, "output_tokens": None, "thoughts_tokens": None}
    um = getattr(response, "usage_metadata", None)
    if um is not None:
        usage["input_tokens"] = getattr(um, "prompt_token_count", None)
        usage["output_tokens"] = getattr(um, "candidates_token_count", None)
        usage["thoughts_tokens"] = getattr(um, "thoughts_token_count", None)
    return assistant_text, usage


def limit_exceeded(agent2_output: str) -> bool:
    return bool(re.search(r"LIMIT_EXCEEDED\s*:\s*true", agent2_output, re.I))


def main() -> int:
    parser = argparse.ArgumentParser(description="WFM Agents 1–3 API smoke (Gemini, FOLIO / P-FOLIO / stress).")
    parser.add_argument("--dry-run", action="store_true", help="Parse prompts/examples only; no API.")
    mx = parser.add_mutually_exclusive_group()
    mx.add_argument(
        "--pfolio",
        action="store_true",
        help="Use ## P-FOLIO section (PF-*); writes wfm_pfolio_gemini_*.",
    )
    mx.add_argument(
        "--stress",
        action="store_true",
        help="Use ## STRESS section (R-* / E-*) from wfm_stress_examples_en.md by default; writes wfm_stress_gemini_*.",
    )
    mx.add_argument(
        "--clincon",
        action="store_true",
        help="Use ## CLINCON section (C-*) from wfm_clincon_fragment_examples_en.md by default; writes wfm_clincon_gemini_*.",
    )
    parser.add_argument(
        "--examples",
        type=Path,
        default=EXAMPLES_FILE,
        help="Example markdown (FOLIO+P-FOLIO, or stress/ClinCon file with --stress / --clincon).",
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
        out_prefix = "wfm_stress_gemini"
        report_title = (
            "# WFM automated run — stress harness (R-* / E-*), Agents 1 → 2 → 3, Gemini"
        )
    elif args.clincon:
        clincon_path = args.examples if args.examples != EXAMPLES_FILE else CLINCON_EXAMPLES_FILE
        examples = parse_clincon_examples(clincon_path)
        examples_file_resolved = str(clincon_path.resolve())
        example_set = "clincon"
        out_prefix = "wfm_clincon_gemini"
        report_title = "# WFM automated run — ClinCon fragment smoke (C-*), Agents 1 → 2 → 3, Gemini"
    elif args.pfolio:
        examples = parse_pfolio_examples(args.examples)
        examples_file_resolved = str(args.examples.resolve())
        example_set = "pfolio"
        out_prefix = "wfm_pfolio_gemini"
        report_title = (
            "# WFM automated run — P-FOLIO base text (PF-*), Agents 1 → 2 → 3, Gemini"
        )
    else:
        examples = parse_folio_examples(args.examples)
        examples_file_resolved = str(args.examples.resolve())
        example_set = "folio"
        out_prefix = "wfm_folio_gemini"
        report_title = "# WFM automated run — FOLIO examples (Agents 1 → 2 → 3), Gemini"

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip()
    temperature = float(os.environ.get("GEMINI_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS)))
    thinking_level = env_thinking_level()

    contract_info = {
        "provider": "google_genai",
        "example_set": example_set,
        "model": model,
        "temperature": temperature,
        "max_output_tokens": max_out,
        "thinking_level": (
            thinking_level.value if thinking_level is not None else "omitted_api_default"
        ),
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
        if args.stress:
            set_label = "STRESS (R-* / E-*)"
        elif args.clincon:
            set_label = "CLINCON (C-*)"
        elif args.pfolio:
            set_label = "P-FOLIO (PF-*)"
        else:
            set_label = "FOLIO"
        print("Dry run OK — parsed", len(examples), f"{set_label} examples.")
        for e in examples:
            print(f"  {e.ex_id} ({e.difficulty}) {len(e.text)} chars")
        print("Compound limit injected:", lim)
        print("Thinking level:", contract_info["thinking_level"])
        return 0

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(
            "ERROR: Set GEMINI_API_KEY in "
            f"{REPO_ROOT / '.env'} (see .env.example) or in the environment.",
            file=sys.stderr,
        )
        return 2

    try:
        from google import genai
    except ImportError:
        print("ERROR: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    client = genai.Client(api_key=api_key)

    tl_note = contract_info["thinking_level"]
    if tl_note == "omitted_api_default":
        tl_report = "*(omitted — API default thinking depth, typically `high` on Gemini 3)*"
    else:
        tl_report = f"`{tl_note}` (see `GEMINI_THINKING_LEVEL`; default is `low` for parity with non–extended-thinking Claude runs)"

    if example_set == "pfolio":
        set_bullet = "- **Example set:** `pfolio` (P-FOLIO base text, PF-* blocks in source markdown)"
    elif example_set == "stress":
        set_bullet = "- **Example set:** `stress` (`test_sets/wfm_stress_examples_en.md`, ## STRESS)"
    elif example_set == "clincon":
        set_bullet = "- **Example set:** `clincon` (`test_sets/wfm_clincon_fragment_examples_en.md`, ## CLINCON)"
    else:
        set_bullet = "- **Example set:** `folio` (F-* blocks)"
    report_lines: list[str] = [
        report_title,
        "",
        f"**UTC timestamp:** {stamp}",
        "",
        "## Contract (this run)",
        "",
        set_bullet,
        f"- **Model:** `{model}`",
        f"- **Temperature:** `{temperature}`",
        f"- **Max output tokens:** `{max_out}`",
        f"- **Thinking level:** {tl_report}",
        f"- **Compound operator limit (injected):** `{lim}`",
        "- **Agent 4:** skipped (no user disagreement simulation)",
        "",
        "Full table: `test_sets/wfm_api_contract_gemini.md`",
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
                    "reason": "Agent 2 emitted LIMIT_EXCEEDED — pipeline would terminate before Agent 3 per WFM.",
                }
                report_lines.append("### Agent 3")
                report_lines.append("")
                report_lines.append(
                    "*SKIPPED — Agent 2 returned LIMIT_EXCEEDED (WFM would reset to user input).*"
                )
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
