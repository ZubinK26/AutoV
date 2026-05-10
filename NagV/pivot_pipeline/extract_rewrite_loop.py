"""Interactive extract: on ABORT, scope-rewrite + confirm + WFM + retry; drop line only with consent."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from pivot_pipeline.exceptions import PivotPipelineUserAbort
from pivot_pipeline.extract import ExtractAbort, _extract_prompt_template, extract_one_line_with_repairs
from pivot_pipeline.extract_scope_rewrite import (
    normalize_operator_hint_input,
    run_scope_rewrite,
    scope_rewrite_hint_max_chars,
)
from pivot_pipeline.llm import pivot_llm_complete
from pivot_wfm.wfm_one_line import run_pivot_wfm_one_line


def _max_scope_proposals_per_abort() -> int:
    raw = os.getenv("PIVOT_SCOPE_REWRITE_MAX_PROPOSALS_PER_LINE", "3").strip()
    try:
        n = int(raw)
        return max(1, min(n, 10))
    except ValueError:
        return 3


def extract_rules_with_abort_rewrite(
    lines: list[str],
    *,
    work_dir: Path,
    repo_root: Path,
    print_fn: Callable[..., None] = print,
    input_fn: Callable[[str], str],
    llm: Callable[..., str] = pivot_llm_complete,
) -> list[dict[str, Any]]:
    """
    Sequential extraction; on :class:`ExtractAbort`, loop scope-rewrite proposals (budget
    ``PIVOT_SCOPE_REWRITE_MAX_PROPOSALS_PER_LINE``), then offer abort vs **drop rule**
    (restarts extraction on the shortened list). Mutates ``lines`` in place.
    """
    tmpl = _extract_prompt_template()
    log_path = work_dir / "extract_rewrite_log.jsonl"
    scratch_root = work_dir / "wfm_rewrite_scratches"
    scratch_root.mkdir(parents=True, exist_ok=True)
    drop_log_path = work_dir / "dropped_rules_log.jsonl"

    def extract_all(cur_lines: list[str]) -> list[dict[str, Any]]:
        rules_out: list[dict[str, Any]] = []
        i = 0
        while i < len(cur_lines):
            line_no = i + 1
            while True:
                try:
                    rule = extract_one_line_with_repairs(
                        line_no,
                        cur_lines[i],
                        tmpl=tmpl,
                        llm=llm,
                        prior_rules=list(rules_out),
                    )
                    rules_out.append(rule)
                    i += 1
                    break
                except ExtractAbort as e:
                    print_fn("\n--- Extract ABORT — scope rewrite ---\n")
                    print_fn(f"Line {line_no}: {cur_lines[i]!r}\n")

                    got_accepted_line = False
                    pending_operator_hint: str | None = None
                    for prop_ix in range(_max_scope_proposals_per_abort()):
                        hint_for_call = pending_operator_hint
                        pending_operator_hint = None
                        print_fn(
                            f"[scope rewrite proposal {prop_ix + 1}/{_max_scope_proposals_per_abort()}]\n"
                        )
                        try:
                            proposal = run_scope_rewrite(
                                cur_lines[i],
                                extractor_abort_text=e.raw,
                                operator_hint=hint_for_call,
                                llm=llm,
                            )
                        except Exception as ex:
                            print_fn(f"[extract] scope_rewrite failed: {ex}\n")
                            raise e from ex

                        print_fn("**Proposed rewrite (LLM)**\n")
                        print_fn(proposal["rewritten_line"])
                        print_fn("\n**Semantic deltas**\n")
                        for d in proposal["semantic_deltas"]:
                            print_fn(f"- {d}")
                        if proposal.get("fidelity_notes"):
                            print_fn(f"\n**Fidelity** — {proposal['fidelity_notes']}\n")

                        ans = input_fn(
                            "Accept rewrite and run through pivot WFM? [y/N/skip to next proposal]: "
                        ).strip().lower()
                        record: dict[str, Any] = {
                            "line_index": line_no,
                            "original_line": cur_lines[i],
                            "proposal_index": prop_ix,
                            "accepted": ans in ("y", "yes"),
                            "proposal": proposal,
                        }
                        if ans not in ("y", "yes"):
                            hint_raw = input_fn(
                                "Optional hint for the next proposal "
                                f"(Enter = none; max {scope_rewrite_hint_max_chars()} chars): "
                            )
                            rec_hint = normalize_operator_hint_input(hint_raw)
                            pending_operator_hint = rec_hint or None
                            record["operator_hint_submitted"] = pending_operator_hint
                            with log_path.open("a", encoding="utf-8") as lf:
                                lf.write(json.dumps(record, ensure_ascii=False) + "\n")
                            continue

                        try:
                            wfm_line = run_pivot_wfm_one_line(
                                proposal["rewritten_line"],
                                repo_root=repo_root,
                                scratch_parent=scratch_root,
                                print_fn=print_fn,
                            )
                        except Exception as ex:
                            print_fn(f"[extract] WFM one-line failed: {ex}\n")
                            record["wfm_error"] = str(ex)
                            with log_path.open("a", encoding="utf-8") as lf:
                                lf.write(json.dumps(record, ensure_ascii=False) + "\n")
                            continue

                        print_fn(f"\n**After WFM:** {wfm_line!r}\n")
                        cur_lines[i] = wfm_line
                        record["wfm_normalized_line"] = wfm_line
                        with log_path.open("a", encoding="utf-8") as lf:
                            lf.write(json.dumps(record, ensure_ascii=False) + "\n")
                        got_accepted_line = True
                        break

                    if got_accepted_line:
                        continue

                    print_fn(
                        "\nAll rewrite proposals for this line were refused or WFM failed.\n"
                    )
                    print_fn(
                        "Policy would be **incomplete** if you drop this rule.\n"
                        "[a] Abort entire run\n"
                        "[d] Drop this rule and continue with an incomplete policy\n"
                    )
                    final = input_fn("Choice [a/d]: ").strip().lower()
                    if final not in ("d", "drop"):
                        raise PivotPipelineUserAbort(
                            f"operator aborted at extract line {line_no} after failed rewrites"
                        ) from e

                    dropped = cur_lines.pop(i)
                    rec = {"line_index": line_no, "dropped_line": dropped, "reason": "extract_abort_budget_exhausted"}
                    with drop_log_path.open("a", encoding="utf-8") as lf:
                        lf.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print_fn(f"[extract] Dropped line {line_no}: {dropped!r}\n")
                    # Restart extraction: rule ids align with new line list
                    return extract_all(cur_lines)

        return rules_out

    return extract_all(lines)


__all__ = ["extract_rules_with_abort_rewrite"]
