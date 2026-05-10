"""Hard gates: WFM coverage vs source rule count, etc."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from wfm_orchestration.nl_chunk_policy_pipeline import parse_nl_rules

from pivot_pipeline.exceptions import PivotPipelineUserAbort

PROCEED_INCOMPLETE_TOKEN = "PROCEED_INCOMPLETE"
REPAIR_CRITIC_DRIFT_TOKEN = "REPAIR"


def wfm_output_matches_source_rule_count(*, nl_source: Path, wfm_nl_text: str) -> bool:
    n_in = len(parse_nl_rules(nl_source.read_text(encoding="utf-8")))
    n_out = len(parse_nl_rules(wfm_nl_text))
    return n_in == n_out


def enforce_wfm_rule_coverage(
    *,
    nl_source: Path,
    wfm_nl_text: str,
    interactive_policy: bool,
    print_fn: Callable[..., None],
    input_fn: Callable[[str], str],
) -> tuple[bool, bool]:
    """
    Return (proceed, user_accepted_incomplete).

    If counts differ and not interactive, return (False, False) — caller must block.

    If counts differ and interactive, prompt for ``PROCEED_INCOMPLETE`` or abort.
    """
    n_in = len(parse_nl_rules(nl_source.read_text(encoding="utf-8")))
    n_out = len(parse_nl_rules(wfm_nl_text))
    if n_in == n_out:
        return True, False

    print_fn(
        f"\n[policy gate] Source {nl_source.name} has {n_in} rule line(s) after parse, "
        f"but WFM normalized NL has {n_out}. The policy model would not cover every input rule.\n"
    )
    if not interactive_policy:
        return False, False

    print_fn(
        "You may abort and fix WFM output / prompts, or continue acknowledging an **incomplete** policy.\n"
        f"Type exactly {PROCEED_INCOMPLETE_TOKEN} to continue; anything else aborts the run.\n"
    )
    ans = input_fn("> ").strip()
    if ans == PROCEED_INCOMPLETE_TOKEN:
        print_fn("[policy gate] Continuing with user-acknowledged incomplete WFM coverage.\n")
        return True, True
    raise PivotPipelineUserAbort(
        f"WFM rule count mismatch ({n_in} vs {n_out}); operator did not consent to incomplete policy."
    )


__all__ = [
    "PROCEED_INCOMPLETE_TOKEN",
    "REPAIR_CRITIC_DRIFT_TOKEN",
    "enforce_wfm_rule_coverage",
    "wfm_output_matches_source_rule_count",
]
