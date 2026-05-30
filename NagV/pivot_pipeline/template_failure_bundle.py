"""Build deterministic failure bundles for Template Diagnostician."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pivot_pipeline.template_suite.schemas import TemplateInstance, load_suite_path


def load_template_run_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def suite_instance_by_id(suite_path: Path) -> dict[str, dict[str, Any]]:
    suite = load_suite_path(suite_path)
    return {inst.instance_id: inst.model_dump(mode="json") for inst in suite.instances}


def failing_results(report: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in report.get("results") or []:
        if not isinstance(row, dict):
            continue
        v = row.get("verdict")
        if v in ("fail", "inconclusive"):
            out.append(row)
    return out


def _query_rule_id(instance: dict[str, Any]) -> str | None:
    q = instance.get("query")
    if isinstance(q, dict) and q.get("decision_metric") == "rule":
        rid = q.get("rule_id")
        return str(rid) if rid else None
    return None


def _instance_world_summary(instance: dict[str, Any]) -> dict[str, Any]:
    kind = instance.get("template_kind")
    if kind == "boundary":
        return {"world_base": instance.get("world_base"), "axis": instance.get("axis_variable")}
    if kind == "counterfactual_flip":
        return {
            "world_base": instance.get("world_base"),
            "world_mutant": instance.get("world_mutant"),
        }
    if kind == "pairwise":
        return {
            "world": instance.get("world"),
            "query_a": instance.get("query_a"),
            "query_b": instance.get("query_b"),
        }
    return {"world": instance.get("world")}


def build_failure_bundles(
    report: dict[str, Any],
    *,
    suite_path: Path,
    linearized_model: str,
    processed_nl: str,
) -> list[dict[str, Any]]:
    """One bundle per fail/inconclusive instance."""
    by_id = suite_instance_by_id(suite_path)
    nl_lines = [ln.strip() for ln in processed_nl.splitlines() if ln.strip()]
    bundles: list[dict[str, Any]] = []
    for row in failing_results(report):
        iid = str(row.get("instance_id", ""))
        inst = by_id.get(iid, {})
        bundles.append(
            {
                "instance_id": iid,
                "template_kind": row.get("template_kind") or inst.get("template_kind"),
                "verdict": row.get("verdict"),
                "actual": row.get("actual"),
                "golden": row.get("golden"),
                "diff": row.get("diff"),
                "instance": inst,
                "instance_world_summary": _instance_world_summary(inst),
                "query_rule_id": _query_rule_id(inst),
                "nl_lines": nl_lines,
            }
        )
    _ = linearized_model  # passed to diagnostician prompt wholesale
    return bundles


def report_needs_diagnostic(report: dict[str, Any]) -> bool:
    s = report.get("summary") or {}
    return int(s.get("failed", 0)) + int(s.get("inconclusive", 0)) > 0


__all__ = [
    "build_failure_bundles",
    "failing_results",
    "load_template_run_report",
    "report_needs_diagnostic",
    "suite_instance_by_id",
]
