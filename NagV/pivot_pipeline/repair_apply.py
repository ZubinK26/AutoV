"""Apply repaired rules and refresh pivot artifacts (shared by repair loops)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pivot_pipeline.backtranslate import meta_scheme_to_markdown
from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.linearize_rules import build_and_write_linearized, linearized_model_artifact_path
from pivot_pipeline.precheck import run_precheck
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
) -> tuple[list[dict[str, Any]], Any, str, dict[str, Any], bool, list[Any], str | None]:
    """
    Compile ``rules``, write extracts, Z3, synthetic, precheck, optional linearization.

    Returns ``(rules, meta, synth, z3_result, precheck_ok, precheck_issues, linearized)``.
    """
    meta = load_rules_and_compile(policy_id, rules)
    extracted_path = work_dir / "rules_extracted.json"
    extracted_path.write_text(
        json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary["rules_extracted"] = str(extracted_path.resolve())
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
    (work_dir / after_rules_basename).write_text(
        json.dumps({"policy_id": policy_id, "rules": rules}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    linearized: str | None = None
    if refresh_linearized:
        linearized = build_and_write_linearized(work_dir=work_dir, rules=rules)
        summary["linearized_model_for_cross_critic"] = str(
            linearized_model_artifact_path(work_dir).resolve()
        )
    return rules, meta, synth, z3_result, ok, issues, linearized


__all__ = ["apply_repaired_rules_and_refresh"]
