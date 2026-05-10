"""Deterministic NL-ish rendering of a MetaScheme (Phase 4, machine side)."""

from __future__ import annotations

from pivot_pipeline.ir import MetaScheme, Preemption


def meta_scheme_to_markdown(meta: MetaScheme) -> str:
    lines: list[str] = [
        f"# Synthetic policy ({meta.policy_id})",
        f"Semantics: {meta.policy_semantics_version}",
        "",
        "## Rules",
    ]
    for r in meta.rules:
        lines.append(f"- **{r.rule_id}** ({r.template_class}) applies_to={r.applies_to} overrides={r.overrides}")

    if any(isinstance(r, Preemption) for r in meta.rules):
        lines.append("")
        lines.append("## Pathway note (v1)")
        lines.append(
            "Evaluation pathways list **`must_satisfy_all`** entries for **non-PREEMPTION** rules only. "
            "**PREEMPTION** rules still appear under **Rules** above and are applied in the policy checker (Z3); "
            "their omission from `must_satisfy_all` is by design, not a missing obligation."
        )
        lines.append("")
        lines.append("### PREEMPTION detail")
        for r in meta.rules:
            if not isinstance(r, Preemption):
                continue
            tgt = r.target_rule_id if r.target_rule_id else "(none)"
            lines.append(
                f"- **{r.rule_id}**: action={r.action.value}, target_rule_id={tgt}"
            )

    lines.append("")
    lines.append("## Pathways")
    for pw in meta.evaluation_pathways:
        lines.append(f"### {pw.pathway_id}")
        if getattr(pw, "description", None) and str(pw.description).strip():
            lines.append(f"- description: {pw.description}")
        lines.append(f"- must_satisfy_all: {pw.must_satisfy_all}")
        lines.append(f"- must_not_trigger: {pw.must_not_trigger}")
    return "\n".join(lines) + "\n"
