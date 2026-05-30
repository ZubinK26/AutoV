"""Human-readable policy-case narrative (deterministic + optional LLM)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pivot_pipeline.external_tester.api_retry import call_with_api_retries
from pivot_pipeline.external_tester.llm import external_llm_complete
from pivot_pipeline.external_tester.pathway_sufficiency import PathwaySufficiencyReportV1
from pivot_pipeline.external_tester.policy_query import PolicyQueryResultV1
from pivot_pipeline.external_tester.tier_programmatic import ProgrammaticFillReportV1
from pivot_pipeline.external_tester.tier_speculative import SpeculativeFillV1
from pivot_pipeline.paths import PROMPTS_DIR


def narrative_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    raw = os.getenv("PIVOT_CASE_NARRATIVE", "on").strip().lower()
    return raw not in ("off", "false", "0", "no")


def _deterministic_narrative(
    *,
    pathway_id: str,
    sufficiency: PathwaySufficiencyReportV1,
    tier1: PolicyQueryResultV1 | None,
    tier2: ProgrammaticFillReportV1 | None,
    tier3: SpeculativeFillV1 | None,
) -> str:
    lines = [
        "# Policy case narrative",
        "",
        f"**Pathway:** `{pathway_id}`",
        "",
        "## Tier 1 — document strict",
        "",
    ]
    if sufficiency.tier1_complete:
        lines.append("Pathway evidence is **complete** for a tier-1 evaluation.")
    else:
        lines.append(
            "**Insufficient evidence** for tier-1. Missing grounded variables:"
        )
        for m in sufficiency.missing:
            rules = ", ".join(m.rule_ids) if m.rule_ids else "—"
            lines.append(f"- `{m.variable}` ({m.reason}; rules: {rules})")

    if tier1 is not None:
        lines.extend(
            [
                "",
                f"Tier-1 strict compatibility: **{tier1.compatibility}** "
                f"(Z3: {tier1.z3_status}).",
            ]
        )
    else:
        lines.append("")
        lines.append("Tier-1 strict query was **not run** (blocked by sufficiency).")

    lines.extend(["", "## Tier 2 — programmatic what-if", ""])
    if tier2 and tier2.inferences:
        lines.append(
            f"Filled {len(tier2.inferences)} gap(s) via rule evaluation "
            f"({', '.join(tier2.filled_variables)})."
        )
        if tier2.tier2_query:
            lines.append(
                f"Hypothetical compatibility: **{tier2.tier2_query.compatibility}** "
                f"(Z3: {tier2.tier2_query.z3_status})."
            )
    else:
        lines.append("No programmatic fills applied.")

    lines.extend(["", "## Tier 3 — speculative (unverified)", ""])
    if tier3 and tier3.suggestions:
        for s in tier3.suggestions:
            cites = s.provenance_audit.line_numbers
            lines.append(
                f"- `{s.variable}` = {s.value!r} ({s.confidence}): "
                f"{s.provenance_audit.rationale or s.basis} [lines {cites}]"
            )
        if tier3.tier3_query:
            lines.append(
                f"\nSpeculative-world compatibility: **{tier3.tier3_query.compatibility}** "
                f"(Z3: {tier3.tier3_query.z3_status})."
            )
    elif tier3 and tier3.skipped:
        lines.append(f"Skipped: {tier3.skip_reason or 'no suggestions'}.")
    else:
        lines.append("No speculative suggestions.")

    lines.append("")
    lines.append(
        "_Tier 2/3 results are weak diagnostics and do not change the tier-1 outcome._"
    )
    return "\n".join(lines) + "\n"


def write_case_narrative(
    work_dir: Path,
    *,
    pathway_id: str,
    sufficiency: PathwaySufficiencyReportV1,
    tier1: PolicyQueryResultV1 | None = None,
    tier2: ProgrammaticFillReportV1 | None = None,
    tier3: SpeculativeFillV1 | None = None,
    use_llm: bool | None = None,
) -> Path:
    """Write policy_case_narrative.md; optional LLM polish when enabled and available."""
    text = _deterministic_narrative(
        pathway_id=pathway_id,
        sufficiency=sufficiency,
        tier1=tier1,
        tier2=tier2,
        tier3=tier3,
    )

    if narrative_enabled(use_llm):
        bundle = {
            "pathway_id": pathway_id,
            "tier1_complete": sufficiency.tier1_complete,
            "missing": [m.model_dump(mode="json") for m in sufficiency.missing],
            "tier1": tier1.model_dump(mode="json") if tier1 else None,
            "tier2": tier2.model_dump(mode="json") if tier2 else None,
            "tier3": tier3.model_dump(mode="json") if tier3 else None,
        }
        template = (PROMPTS_DIR / "external_case_narrative.md").read_text(encoding="utf-8")
        prompt = f"{template}\n\n---\n\n```json\n{json.dumps(bundle, indent=2)}\n```\n"
        try:
            llm_text = call_with_api_retries(
                lambda: external_llm_complete(prompt, stage="review"),
                label="case_narrative",
            )
            if llm_text.strip():
                text = llm_text.strip() + "\n"
        except (RuntimeError, OSError, ValueError):
            pass

    path = work_dir / "policy_case_narrative.md"
    path.write_text(text, encoding="utf-8")
    return path


__all__ = ["narrative_enabled", "write_case_narrative"]
