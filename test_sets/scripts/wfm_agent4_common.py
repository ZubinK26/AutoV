"""Shared helpers for Agent 4 runners (payload, merge preview, Gemini call)."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEST_SETS = SCRIPT_DIR.parent
REPO_ROOT = TEST_SETS.parent
WFM_DIR = REPO_ROOT / "WFM"
PROMPTS_DIR = WFM_DIR / "prompts"
RESULTS_DIR = TEST_SETS / "run_results"

DEFAULT_MODEL = "gemini-3.1-pro-preview"
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


def extract_system_prompt(md_path: Path) -> str:
    raw = md_path.read_text(encoding="utf-8")
    m = re.search(r"```\n(.*?)```", raw, re.DOTALL)
    if not m:
        raise ValueError(f"No ``` fenced system block in {md_path}")
    return m.group(1).strip()


def limit_exceeded(agent2_output: str) -> bool:
    return bool(re.search(r"LIMIT_EXCEEDED\s*:\s*true", agent2_output, re.I))


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def is_eligible(row: dict) -> bool:
    """Agent 3 ran with output (not skipped) and Agent 2 was not LIMIT_EXCEEDED."""
    a2 = row.get("agent_2") or {}
    out2 = a2.get("output") or ""
    if limit_exceeded(out2):
        return False
    a3 = row.get("agent_3") or {}
    if a3.get("skipped"):
        return False
    if not str(a3.get("output") or "").strip():
        return False
    return True


def _unquote_inner(raw: str) -> str:
    return raw.replace(r"\"", '"').replace(r"\\", "\\")


def parse_numbered_lines(agent2_output: str) -> dict[int, str]:
    """Parse Agent 2 SUCCESS lines: N. \"text\" -> index -> inner text."""
    out: dict[int, str] = {}
    for m in re.finditer(
        r"(?m)^(\d+)\.\s*\"((?:[^\"\\\\]|\\\\.)*)\"\s*$",
        agent2_output,
    ):
        idx = int(m.group(1))
        inner = _unquote_inner(m.group(2))
        out[idx] = inner
    return out


def parse_agent3_effective_lines(
    agent3_output: str,
    agent2_output: str,
) -> tuple[dict[int, str], list[str]]:
    """
    Option A merge base: per Agent 2 sub-statement index, use current text from Agent 3
    (PASS / REWRITE / OUT_OF_SCOPE quoted payload). Starts from Agent 2, overlays Agent 3.
    """
    warnings: list[str] = []
    base = parse_numbered_lines(agent2_output)
    if not base:
        return {}, ["No Agent 2 numbered lines to merge with."]

    effective: dict[int, str] = dict(base)
    # Optional leading "k. " from some model / markdown wrappers.
    line_prefix = r"(?:\d+\.\s+)?"
    num_pat = re.compile(
        rf"^{line_prefix}(PASS|REWRITE|OUT_OF_SCOPE):\s*(\d+)\.\s*"
        r"\"((?:[^\"\\]|\\.)*)\"\s*(?:\|.*)?\s*$"
    )
    unnum_pat = re.compile(
        rf"^{line_prefix}(PASS|REWRITE|OUT_OF_SCOPE):\s*"
        r"\"((?:[^\"\\]|\\.)*)\"\s*(?:\|.*)?\s*$"
    )

    for raw_line in agent3_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = num_pat.match(line)
        if m:
            idx = int(m.group(2))
            inner = _unquote_inner(m.group(3))
            if idx not in base:
                warnings.append(
                    f"Agent 3 references unknown index {idx} (ignored for merge base)."
                )
                continue
            effective[idx] = inner
            if m.group(1) == "PASS" and base[idx].strip() != inner.strip():
                warnings.append(
                    f"PASS line {idx} text differs from Agent 2; using Agent 3 line."
                )
            continue
        m2 = unnum_pat.match(line)
        if not m2:
            continue
        inner = _unquote_inner(m2.group(2))
        matches = [i for i, t in base.items() if t.strip() == inner.strip()]
        if not matches:
            warnings.append(
                "Unnumbered Agent 3 line did not match any Agent 2 statement (skipped)."
            )
            continue
        if len(matches) > 1:
            warnings.append(
                f"Unnumbered line matched multiple indices {matches}; using {matches[0]}."
            )
        idx = matches[0]
        effective[idx] = inner
        if m2.group(1) == "PASS" and base[idx].strip() != inner.strip():
            warnings.append(
                f"PASS (unnumbered) line {idx} text differs from Agent 2; using Agent 3 line."
            )

    return effective, warnings


def extract_oos_agent2_indices(agent3_output: str, agent2_output: str) -> set[int]:
    """
    Agent 3 lines tagged OUT_OF_SCOPE map to Agent 2 sub-statement indices when the line
    starts with OUT_OF_SCOPE: N. or when the quoted payload matches an Agent 2 statement.
    """
    indices: set[int] = set()
    base = parse_numbered_lines(agent2_output)
    for line in agent3_output.splitlines():
        line_st = line.strip()
        if not line_st.startswith("OUT_OF_SCOPE"):
            continue
        m_num = re.match(r"OUT_OF_SCOPE:\s*(\d+)\.\s*\"", line_st)
        if m_num:
            ix = int(m_num.group(1))
            if ix in base:
                indices.add(ix)
            continue
        m_q = re.search(r"OUT_OF_SCOPE:\s*\"((?:[^\"\\\\]|\\\\.)*)\"", line_st)
        if m_q:
            inner = _unquote_inner(m_q.group(1))
            for idx, txt in base.items():
                if txt.strip() == inner.strip():
                    indices.add(idx)
                    break
    return indices


def agent3_has_out_of_scope(agent3_output: str) -> bool:
    return bool(re.search(r"(?m)^\s*OUT_OF_SCOPE\s*:", agent3_output))


def parse_wfm_patch(text: str) -> dict | None:
    m = re.search(r"```wfm_patch\s*\n", text, re.IGNORECASE)
    if not m:
        return None
    start = m.end()
    end = text.find("\n```", start)
    if end == -1:
        return None
    blob = text[start:end].strip()
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def build_merge_preview(
    *,
    base_lines: dict[int, str],
    omit_indices: set[int],
    replacements: list[dict],
) -> str:
    rep_by_idx: dict[int, str] = {}
    for r in replacements:
        idx = int(r["index"])
        rep_by_idx[idx] = str(r["text"]).strip()
    merged: dict[int, str] = {}
    for idx in sorted(base_lines.keys()):
        if idx in omit_indices:
            continue
        merged[idx] = rep_by_idx.get(idx, base_lines[idx])
    ordered = [merged[k] for k in sorted(merged.keys())]
    return "\n".join(f"{i}. {t}" for i, t in enumerate(ordered, start=1)) + "\n"


def build_user_payload(
    *,
    row: dict,
    run_path: Path,
    disagree: list[int],
    comments: list[str],
    omit_confirmed: list[int],
) -> str:
    ex_id = row.get("example_id", "?")
    diff = row.get("difficulty", "")
    a2 = (row.get("agent_2") or {}).get("output") or ""
    a3 = (row.get("agent_3") or {}).get("output") or ""
    if len(comments) != len(disagree):
        raise ValueError(
            f"Need one comment per disagreed line: {len(disagree)} indices, {len(comments)} comments"
        )
    comments_block = "\n".join(
        f"- Line {d}: {c!r}" for d, c in zip(disagree, comments, strict=False)
    )
    omit_s = ", ".join(str(x) for x in sorted(omit_confirmed)) or "(none)"
    dis_s = ", ".join(str(x) for x in disagree) or "(none)"
    return f"""## Structured disagreement payload (orchestration to Agent 4)

### Example
- **example_id:** `{ex_id}`
- **difficulty:** {diff}
- **source_run:** `{run_path.as_posix()}`

### Numbered sub-statements (Agent 2 output, verbatim)
{a2}

### Scope outcomes (Agent 3 output, verbatim)
{a3}

### User disagreed line indices (1-based, confirmation UI)
{dis_s}

### User comments (one per disagreed line, same order)
{comments_block}

### User-confirmed omit indices (OUT_OF_SCOPE or other; from UI only)
{omit_s}
"""


def merge_preview_from_response(
    *,
    assistant_text: str,
    row: dict,
    disagree: list[int],
    omit_confirmed: list[int],
) -> str:
    patch = parse_wfm_patch(assistant_text)
    a2 = (row.get("agent_2") or {}).get("output") or ""
    a3 = (row.get("agent_3") or {}).get("output") or ""
    base_a2 = parse_numbered_lines(a2)
    if not base_a2:
        return "\n(Could not parse Agent 2 numbered lines for merge preview.)\n"
    base_merge, merge_notes = parse_agent3_effective_lines(a3, a2)
    if not base_merge:
        return "\n(Could not build Agent 3 merge base for preview.)\n"
    if patch is None:
        return "\n(No valid ```wfm_patch``` JSON found in response — merge preview skipped.)\n"
    reps = patch.get("replacements") or []
    if not isinstance(reps, list):
        return "\n(invalid replacements in patch)\n"
    dset, oset = set(disagree), set(omit_confirmed)
    bad: list[int] = []
    for r in reps:
        try:
            ix = int(r["index"])
        except (KeyError, TypeError, ValueError):
            bad.append(-1)
            continue
        if ix not in dset or ix in oset:
            bad.append(ix)
    if bad:
        return f"\n(merge preview skipped: patch indices not in disagreed∖omit — {bad})\n"
    try:
        prev = build_merge_preview(
            base_lines=base_merge,
            omit_indices=set(omit_confirmed),
            replacements=reps,
        )
        out = (
            "\n--- Style A merge preview (orchestration; validate before trust) ---\n\n" + prev
        )
        if merge_notes:
            note_txt = "; ".join(merge_notes[:6])
            more = f" (+{len(merge_notes) - 6} more)" if len(merge_notes) > 6 else ""
            out += f"\n(Merge base: Agent 3 overlay notes: {note_txt}{more})\n"
        return out
    except Exception as e:
        return f"\n(merge preview error: {e})\n"


def call_agent4_gemini(
    *,
    user_payload: str,
    row: dict,
    run_path: Path,
    ex_id: str,
    merge_preview: bool,
    disagree: list[int],
    omit_confirmed: list[int],
    out: Path | None,
) -> int:
    load_repo_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print(
            f"ERROR: Set GEMINI_API_KEY in {REPO_ROOT / '.env'} (see .env.example).",
            file=sys.stderr,
        )
        return 2

    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError:
        print("ERROR: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    system = extract_system_prompt(PROMPTS_DIR / "agent_4_user_interaction.md")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL).strip()
    temperature = float(os.environ.get("GEMINI_TEMPERATURE", str(DEFAULT_TEMPERATURE)))
    max_out = int(os.environ.get("GEMINI_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS)))

    thinking_level = None
    raw_tl = os.environ.get("GEMINI_THINKING_LEVEL", "").strip().lower()
    if raw_tl not in ("", "unspecified", "api_default", "default"):
        if raw_tl == "low":
            thinking_level = genai_types.ThinkingLevel.LOW
        elif raw_tl == "medium":
            thinking_level = genai_types.ThinkingLevel.MEDIUM
        elif raw_tl == "high":
            thinking_level = genai_types.ThinkingLevel.HIGH
        else:
            thinking_level = genai_types.ThinkingLevel.LOW

    cfg_kwargs: dict = {
        "system_instruction": system,
        "temperature": temperature,
        "max_output_tokens": max_out,
    }
    if thinking_level is not None:
        cfg_kwargs["thinking_config"] = genai_types.ThinkingConfig(
            thinking_level=thinking_level,
        )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=user_payload,
        config=genai_types.GenerateContentConfig(**cfg_kwargs),
    )
    assistant_text = (response.text or "").strip()
    print("--- Agent 4 response ---\n")
    print(assistant_text)

    report_extra = ""
    if merge_preview:
        report_extra = merge_preview_from_response(
            assistant_text=assistant_text,
            row=row,
            disagree=disagree,
            omit_confirmed=omit_confirmed,
        )
    if report_extra:
        print(report_extra)

    if out:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        out_path = out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        body = (
            f"# Agent 4 run from prior WFM JSONL\n\n**UTC:** {stamp}\n**Source:** `{run_path.as_posix()}`\n"
            f"**Example:** `{ex_id}`\n\n## Payload\n\n```\n{user_payload}\n```\n\n## Response\n\n{assistant_text}\n{report_extra}\n"
        )
        out_path.write_text(body, encoding="utf-8")
        print(f"\nWrote: {out_path}")

    return 0
