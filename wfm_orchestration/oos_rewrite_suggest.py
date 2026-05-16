"""After Agent 3, suggest in-scope rewrites for OUT_OF_SCOPE lines (pivot WFM assist)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Callable, TextIO

from wfm_orchestration.gemini_client import call_gemini


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_out_of_scope_entries(agent3_output: str) -> list[tuple[int, str, str]]:
    """``(1-based chunk line index, inner statement text, scope report text)`` for OUT_OF_SCOPE rows."""
    line_prefix = r"(?:\d+\.\s+)?"
    num_pat = re.compile(
        rf"^{line_prefix}OUT_OF_SCOPE:\s*(\d+)\.\s*"
        r"\"((?:[^\"\\]|\\.)*)\"\s*(?:\|\s*(.*))?\s*$"
    )
    out: list[tuple[int, str, str]] = []
    for raw_line in agent3_output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = num_pat.match(line)
        if m:
            idx = int(m.group(1))
            stmt = m.group(2)
            report = (m.group(3) or "").strip()
            out.append((idx, stmt, report))
    return out


def _agent2_line(agent2_output: str, index_1based: int) -> str | None:
    for raw in agent2_output.splitlines():
        rs = raw.strip()
        if re.match(rf"^{index_1based}\.\s", rs):
            return rs
    return None


def _load_encodability_contract(max_chars: int = 12000) -> str:
    p = _repo_root() / "NagV" / "pivot_pipeline" / "prompts" / "v1_policy_encodability_contract.md"
    if not p.is_file():
        return ""
    t = p.read_text(encoding="utf-8")
    if len(t) <= max_chars:
        return t
    return t[:max_chars] + "\n\n[… contract truncated …]\n"


_OOS_SUGGEST_SYSTEM = """You assist the WFM confirmation step for a **pivot** (v1 linear IR) policy pipeline.

Agent 3 marked some decomposed lines as OUT_OF_SCOPE. For **each** such line, propose **one** replacement English rule line that is **more likely in-scope** for pivot v1 (static logical constraints, no vague subjective predicates unless made explicit and measurable, avoid irreducible temporal “before/after” ordering unless expressible as state constraints the contract allows).

Output **only** valid JSON (no markdown fences). Schema:
{"suggestions":[{"line_index": <int matching input>,"suggested_line": "<single English rule line>","notes": "<brief tradeoffs or what changed>"}]}

- Include **exactly one** object per OUT_OF_SCOPE line from the input list, same line_index values.
- suggested_line must be one line; no numbering prefix in the string."""


def maybe_print_pivot_oos_rewrite_attempt1(
    *,
    agent2_output: str,
    agent3_output: str,
    wfm_profile: str | None,
    client: Any,
    model: str,
    temperature: float,
    max_output_tokens: int,
    thinking_level: Any,
    print_fn: Callable[..., None],
    stderr: TextIO,
) -> None:
    if (wfm_profile or "").strip().lower() != "pivot":
        return
    raw = os.getenv("PIVOT_WFM_OOS_SUGGEST", "1").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return

    oos = parse_out_of_scope_entries(agent3_output)
    if not oos:
        return

    rows = []
    for idx, stmt, report in oos:
        a2 = _agent2_line(agent2_output, idx)
        rows.append(
            {
                "line_index": idx,
                "agent2_line": a2,
                "out_of_scope_statement": stmt,
                "agent3_scope_report": report,
            }
        )

    contract = _load_encodability_contract()
    user_payload = {
        "out_of_scope_lines": rows,
        "encodability_contract_excerpt": contract or "(no contract file; use pivot v1 linear constraints.)",
    }
    user_text = json.dumps(user_payload, ensure_ascii=False, indent=2)

    print_fn("\n### Automatic in-scope rewrite suggestions (attempt 1 — advisory only)\n")
    print_fn(
        "The handoff is still built from the **Agent 3 verdicts above** until you accept. "
        "Rejecting the package and naming line indices with comments triggers **attempt 2** (Agent 4 merge path).\n"
    )
    try:
        raw_out, _u = call_gemini(
            client,
            model=model,
            system=_OOS_SUGGEST_SYSTEM,
            user=user_text,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            thinking_level=thinking_level,
        )
    except Exception as e:  # noqa: BLE001
        stderr.write(f"[oos_rewrite_suggest] skipped: {e}\n")
        print_fn("(Could not generate automatic suggestions.)\n")
        return

    text = raw_out.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)

    try:
        data = json.loads(text)
        sug = data.get("suggestions")
        if isinstance(sug, list):
            by_ix = {int(x["line_index"]): x for x in sug if isinstance(x, dict) and "line_index" in x}
            for idx, stmt, report in oos:
                block = by_ix.get(idx)
                print_fn(f"**Line {idx}** (was OUT_OF_SCOPE: “{stmt[:200]}{'…' if len(stmt) > 200 else ''}”)\n")
                print_fn(f"- Agent 3 report: {report or '(none)'}\n")
                if block:
                    sl = str(block.get("suggested_line") or "").strip()
                    notes = str(block.get("notes") or "").strip()
                    if sl:
                        print_fn(f"- **Suggested rewrite:** {sl}\n")
                    if notes:
                        print_fn(f"- **Notes:** {notes}\n")
                else:
                    print_fn("- *(No suggestion returned for this index.)*\n")
                print_fn("")
            return
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass

    print_fn(raw_out)
    print_fn("")


__all__ = [
    "maybe_print_pivot_oos_rewrite_attempt1",
    "parse_out_of_scope_entries",
]
