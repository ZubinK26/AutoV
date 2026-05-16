"""Load WFM system prompts (same injection rules as ``run_wfm_folio_gemini``)."""

from __future__ import annotations

import json
from pathlib import Path

from wfm_orchestration.gemini_client import get_gemini_module


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_wfm_prompts(wfm_profile: str | None = None) -> tuple[str, str, str, str, int]:
    """Returns (agent1, agent2, agent3, agent4, compound_limit).

    When ``wfm_profile`` is ``"pivot"``, Agent 2 system text additionally includes
    ``NagV/pivot_wfm/prompts/agent_2_pivot_chunk_cardinality.md`` (one output line per
    chunk input rule). Other profiles omit this block.
    """
    gm = get_gemini_module()
    root = repo_root()
    cfg = json.loads((root / "WFM" / "config" / "wfm.json").read_text(encoding="utf-8"))
    lim = int(cfg.get("compound_operator_limit", 8))
    p1 = gm.extract_system_prompt(root / "WFM" / "prompts" / "agent_1_completeness_ambiguity.md")
    p2 = gm.inject_compound_limit(
        gm.extract_system_prompt(root / "WFM" / "prompts" / "agent_2_decomposition.md"),
        lim,
    )
    if (wfm_profile or "").strip().lower() == "pivot":
        card = root / "NagV" / "pivot_wfm" / "prompts" / "agent_2_pivot_chunk_cardinality.md"
        if card.is_file():
            p2 = f"{p2}\n\n{card.read_text(encoding='utf-8').strip()}\n"
    p3 = gm.extract_system_prompt(root / "WFM" / "prompts" / "agent_3_scope_rewrite.md")
    import sys

    if str(root / "test_sets" / "scripts") not in sys.path:
        sys.path.insert(0, str(root / "test_sets" / "scripts"))
    import wfm_agent4_common as w4  # noqa: E402

    p4 = w4.extract_system_prompt(root / "WFM" / "prompts" / "agent_4_user_interaction.md")
    return p1, p2, p3, p4, lim
