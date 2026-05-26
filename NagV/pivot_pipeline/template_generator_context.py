"""Build deterministic POLICY CONTEXT excerpt for template_generator LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _truncate(s: str, max_len: int, *, label: str) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    head = max_len // 2 - 20
    tail = max_len - head - 20
    return s[:head] + f"\n... [{label} truncated] ...\n" + s[-tail:]


def build_template_generator_context(work_dir: Path, *, max_total_chars: int = 14_000) -> str:
    """Assemble policy excerpt: rules, meta pathway summary, optional synthetic head."""
    work_dir = work_dir.resolve()
    parts: list[str] = []

    rules_path = work_dir / "rules_extracted.json"
    if not rules_path.is_file():
        raise FileNotFoundError(f"missing {rules_path}")
    raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))
    policy_id = raw_rules.get("policy_id", "")
    rules = raw_rules.get("rules") or []
    compact = {"policy_id": policy_id, "rules": rules}
    rules_json = json.dumps(compact, indent=2, ensure_ascii=False)

    meta_path = work_dir / "meta_scheme.json"
    meta_note = ""
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        pws = meta.get("evaluation_pathways") or []
        if pws:
            must = pws[0].get("must_satisfy_all") or []
            sorts = meta.get("variable_sorts") or {}
            meta_note = json.dumps(
                {
                    "evaluation_pathway_0_must_satisfy_all": must,
                    "variable_sorts": sorts,
                },
                indent=2,
                ensure_ascii=False,
            )

    synth_path = work_dir / "synthetic_en.md"
    synth_excerpt = ""
    if synth_path.is_file():
        synth_excerpt = _truncate(synth_path.read_text(encoding="utf-8"), 4_000, label="synthetic_en.md")

    from pivot_pipeline.ir_vnext import VNEXT_TEMPLATE_CLASSES

    vnext_ids = [
        r.get("rule_id")
        for r in rules
        if str(r.get("template_class")) in VNEXT_TEMPLATE_CLASSES
    ]
    vnext_note = ""
    if vnext_ids:
        vnext_note = (
            "### vNext expansion rules (prioritize tests for these rule_ids)\n"
            f"Expansion template rule_ids in extract JSON: {json.dumps(vnext_ids, ensure_ascii=False)}\n"
            "Author instances that set worlds exercising variables in clauses, terms, rows, "
            "switch cases, and INT_RANGE bounds. meta_scheme lists **lowered** core rule_ids; "
            "still cite expansion rule_ids above when targeting template shape.\n\n"
        )

    temporal_vars: list[str] = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        tc = str(r.get("template_class") or "")
        if tc in ("LOGICAL_IMPLICATION", "VARIABLE_RELATIONAL", "EXCLUSIVE_CHOICE", "K_OF_N"):
            blob = json.dumps(r, ensure_ascii=False)
            for token in (
                "step_",
                "start_",
                "rank_",
                "deadline_",
                "phase",
                "workflow_state",
                "_verified",
                "_complete",
            ):
                if token in blob:
                    temporal_vars.append(tc)
                    break
    temporal_note = ""
    if temporal_vars:
        temporal_note = (
            "### Temporal-shaped rules (prerequisite / order / k-of-n)\n"
            "Policy includes implication chains, scalar order, or verification flags. "
            "Set worlds so step/verification flags and order scalars are internally consistent; "
            "add one scenario that breaks prerequisite order when multiple step rules exist.\n\n"
        )

    assessment_path = work_dir / "linearized_model_for_assessment.txt"
    assessment_excerpt = ""
    if assessment_path.is_file():
        assessment_excerpt = _truncate(
            assessment_path.read_text(encoding="utf-8"), 3_500, label="assessment linearized"
        )

    chunks: list[str] = ["## POLICY CONTEXT", "", "### rules_extracted.json (full)", rules_json, ""]
    if vnext_note:
        chunks.extend([vnext_note])
    if temporal_note:
        chunks.extend([temporal_note])
    if assessment_excerpt:
        chunks.extend(["### linearized_model_for_assessment.txt (excerpt)", assessment_excerpt, ""])
    if meta_note:
        chunks.extend(["### meta_scheme (pathway + sorts)", meta_note, ""])
    if synth_excerpt:
        chunks.extend(["### synthetic_en.md (excerpt)", synth_excerpt, ""])

    out = "\n".join(chunks).strip()
    if len(out) > max_total_chars:
        out = _truncate(out, max_total_chars, label="POLICY CONTEXT")
    return out
