"""Apply Agent 4 ``WFM_PATCH`` + omit list → Style A NL for Agent 1 re-entry."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO / "test_sets" / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "test_sets" / "scripts"))

import wfm_agent4_common as w4  # noqa: E402


def style_a_merged_nl(
    assistant_text: str,
    *,
    agent2_output: str,
    agent3_output: str,
    disagree_1based: list[int],
    omit_confirmed_1based: list[int],
) -> str:
    """
    Same merge as ``merge_preview_from_response`` but returns **only** the merged body
    (numbered lines, trailing newline) suitable as **user** input to Agent 1.
    """
    patch = w4.parse_wfm_patch(assistant_text)
    if patch is None:
        raise ValueError("Agent 4 response has no parseable ```wfm_patch``` JSON block")
    base_merge, _ = w4.parse_agent3_effective_lines(agent3_output, agent2_output)
    if not base_merge:
        raise ValueError("Could not build merge base from Agent 3/2")
    reps = patch.get("replacements") or []
    if not isinstance(reps, list):
        raise ValueError("Invalid patch.replacements")
    dset, oset = set(disagree_1based), set(omit_confirmed_1based)
    for r in reps:
        try:
            ix = int(r["index"])
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid replacement index: {r!r}") from e
        if ix not in dset or ix in oset:
            raise ValueError(f"Patch index {ix} not in disagreed∖omit")
    return w4.build_merge_preview(
        base_lines=base_merge,
        omit_indices=set(omit_confirmed_1based),
        replacements=reps,
    )
