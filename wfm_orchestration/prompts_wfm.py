"""Load WFM system prompts (same injection rules as ``run_wfm_folio_gemini``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from wfm_orchestration.gemini_client import get_gemini_module

WfmProfile = Literal["asp", "smt"]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def wfm_assets_root(profile: WfmProfile, *, root: Path | None = None) -> Path:
    """
    Root directory for WFM assets (config + prompts + normative ``Agent_WFM.md``).

    - ``asp`` — ``asp/wfm/`` (ClinCon-safe scope; ClinCon / ``asp_pipeline`` handoffs).
    - ``smt`` — ``smt/wfm/`` (decidable many-sorted FOL scope per ``pipeline_spec.md``;
      snapshot from frozen ``smt-pipeline``).
    """
    base = root or repo_root()
    if profile == "asp":
        return base / "asp" / "wfm"
    return base / "smt" / "wfm"


def load_wfm_prompts(profile: WfmProfile = "asp") -> tuple[str, str, str, str, int]:
    """Returns (agent1, agent2, agent3, agent4, compound_limit)."""
    gm = get_gemini_module()
    root = repo_root()
    wroot = wfm_assets_root(profile, root=root)
    cfg_path = wroot / "config" / "wfm.json"
    if not cfg_path.is_file():
        raise FileNotFoundError(
            f"WFM config missing for profile {profile!r}: {cfg_path} "
            f"(expected {'asp/wfm/' if profile == 'asp' else 'smt/wfm/'})"
        )
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    lim = int(cfg.get("compound_operator_limit", 8))
    pdir = wroot / "prompts"
    p1 = gm.extract_system_prompt(pdir / "agent_1_completeness_ambiguity.md")
    p2 = gm.inject_compound_limit(
        gm.extract_system_prompt(pdir / "agent_2_decomposition.md"),
        lim,
    )
    p3 = gm.extract_system_prompt(pdir / "agent_3_scope_rewrite.md")
    import sys

    if str(root / "test_sets" / "scripts") not in sys.path:
        sys.path.insert(0, str(root / "test_sets" / "scripts"))
    import wfm_agent4_common as w4  # noqa: E402

    p4 = w4.extract_system_prompt(pdir / "agent_4_user_interaction.md")
    return p1, p2, p3, p4, lim
