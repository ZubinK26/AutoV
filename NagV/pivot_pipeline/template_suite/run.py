"""Orchestrate template suite: load policy, validate, execute, diff, report."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pivot_pipeline.constants import POLICY_SEMANTICS_VERSION_DEFAULT
from pivot_pipeline.ir import load_rules_and_compile
from pivot_pipeline.template_suite.diff import diff_instance
from pivot_pipeline.template_suite.execute_z3 import execute_instance
from pivot_pipeline.template_suite.schemas import load_suite_path, sort_instances
from pivot_pipeline.template_suite.validate import validate_instance


def rules_json_sha256(rules: list[dict]) -> str:
    payload = json.dumps(rules, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class RunSummary:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    inconclusive: int = 0


def load_meta_from_rules_path(path: Path) -> Any:
    data = json.loads(path.read_text(encoding="utf-8"))
    policy_id = data.get("policy_id")
    rules = data.get("rules")
    if not policy_id or not isinstance(rules, list):
        raise ValueError(f"rules_extracted JSON missing policy_id or rules list: {path}")
    return load_rules_and_compile(str(policy_id), rules)


def run_template_suite(
    *,
    suite_path: Path,
    rules_extracted_path: Path,
    out_report_path: Path | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    suite = load_suite_path(suite_path)
    rules_path = rules_extracted_path
    raw_rules = json.loads(rules_path.read_text(encoding="utf-8"))
    rules_list = raw_rules.get("rules") or []
    binding = {
        "rules_sha256": rules_json_sha256(rules_list),
        "policy_id": raw_rules.get("policy_id"),
        "policy_semantics_version": POLICY_SEMANTICS_VERSION_DEFAULT,
    }
    meta = load_meta_from_rules_path(rules_path)

    instances = sort_instances(list(suite.instances))
    summary = RunSummary()
    results: list[dict[str, Any]] = []

    for inst in instances:
        row: dict[str, Any] = {
            "instance_id": inst.instance_id,
            "template_kind": inst.template_kind,
            "verdict": "error",
            "actual": None,
            "golden": getattr(inst, "golden", None),
            "diff": None,
            "error": None,
        }
        try:
            validate_instance(meta, inst)
            actual = execute_instance(meta, inst)
            row["actual"] = actual
            verdict, diff = diff_instance(inst, actual)
            row["verdict"] = verdict
            row["diff"] = diff
            if verdict == "pass":
                summary.passed += 1
            elif verdict == "fail":
                summary.failed += 1
            elif verdict == "inconclusive":
                summary.inconclusive += 1
            else:
                summary.errors += 1
        except Exception as e:
            row["error"] = f"{type(e).__name__}: {e}"
            summary.errors += 1
        results.append(row)

    report: dict[str, Any] = {
        "schema_version": "1",
        "suite_id": suite.suite_id,
        "policy_binding": binding,
        "summary": {
            "passed": summary.passed,
            "failed": summary.failed,
            "errors": summary.errors,
            "inconclusive": summary.inconclusive,
        },
        "results": results,
    }
    if write_report and out_report_path is not None:
        out_report_path.parent.mkdir(parents=True, exist_ok=True)
        out_report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


__all__ = ["run_template_suite", "load_meta_from_rules_path"]
