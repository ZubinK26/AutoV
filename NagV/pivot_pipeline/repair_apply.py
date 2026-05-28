"""Apply repaired rules and refresh pivot artifacts (shared by repair loops)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pivot_pipeline.assessment_linearize import build_and_write_assessment_artifacts
from pivot_pipeline.backtranslate import meta_scheme_to_markdown
from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.precheck import run_precheck
from pivot_pipeline.rules_document import (
    rules_contain_vnext_templates,
    write_rules_document_file,
)
from pivot_pipeline.z3_compile import run_z3_check


def apply_repaired_rules_and_refresh(
    *,
    work_dir: Path,
    policy_id: str,
    rules: list[dict[str, Any]],
    meta_path: Path,
    nl_for_precheck: Path,
    summary: dict[str, Any],
    after_rules_basename: str,
    refresh_linearized: bool = True,
    rules_envelope: dict[str, Any] | None = None,
    skip_vnext_lowering: bool = False,
) -> tuple[list[dict[str, Any]], Any, str, dict[str, Any], bool, list[Any], str | None]:
    """
    Compile ``rules``, write extracts, Z3, synthetic, precheck, optional linearization.

    Returns ``(rules, meta, synth, z3_result, precheck_ok, precheck_issues, linearized)``.
    """
    env = dict(rules_envelope or {})
    doc = write_rules_document_file(
        work_dir / "rules_extracted.json",
        policy_id,
        rules,
        rules_envelope=env,
    )
    summary.update(
        {
            k: doc[k]
            for k in ("policy_semantics_version", "pivot_ir_extensions")
            if k in doc
        }
    )
    if rules_contain_vnext_templates(rules):
        summary["vnext_rules_present"] = True

    meta = load_rules_and_compile(
        policy_id,
        rules,
        skip_vnext_lowering=skip_vnext_lowering,
        policy_semantics_version=doc.get("policy_semantics_version"),
    )
    summary["rules_extracted"] = str((work_dir / "rules_extracted.json").resolve())
    meta_path.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
    summary["meta_scheme"] = str(meta_path.resolve())
    z3_result = run_z3_check(meta)
    summary["z3"] = z3_result
    (work_dir / "z3_result.json").write_text(
        json.dumps(z3_result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    synth = meta_scheme_to_markdown(meta)
    (work_dir / "synthetic_en.md").write_text(synth, encoding="utf-8")
    ok, issues = run_precheck(nl_path=nl_for_precheck, meta=meta)
    summary["precheck_ok"] = ok
    summary["precheck_issues"] = issues
    (work_dir / "precheck.json").write_text(
        json.dumps({"ok": ok, "issues": issues}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_rules_document_file(
        work_dir / after_rules_basename,
        policy_id,
        rules,
        rules_envelope=env,
    )
    linearized: str | None = None
    if refresh_linearized:
        linearized = build_and_write_assessment_artifacts(work_dir=work_dir, rules=rules, summary=summary)
    return rules, meta, synth, z3_result, ok, issues, linearized


__all__ = ["apply_repaired_rules_and_refresh"]
