from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

__all__ = [
    "ConsistencyReport",
    "build_consistency_report",
    "deployment_should_fail",
    "parse_policy_annotations",
    "policy_text_from_path",
    "write_report",
]


@dataclass
class ConsistencyReport:
    policy_version: str
    satisfiable: bool
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    unreachable_rules: list[str] = field(default_factory=list)
    tools_always_legal: list[str] = field(default_factory=list)
    tools_always_illegal: list[str] = field(default_factory=list)
    pairwise_conflicts: list[dict[str, Any]] = field(default_factory=list)

    def to_json_obj(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_json_obj(), indent=indent) + "\n"


@dataclass
class ParsedPolicyHeader:
    policy_version: str
    rule_ids: list[str] = field(default_factory=list)
    covered_tools: list[str] = field(default_factory=list)


RuleTriggerBuilder = Callable[[Any], Any]


def _trigger_goodwill_cap(ctx: Any) -> Any:
    from z3 import And, Bool, Int

    return And(Bool("sim-vulnerable", ctx), Int("sim-proposed-goodwill-pence", ctx) > 50000)


# Reachability: guard satisfiable with policy (Python builders share Z3 context with policy consts).
RULE_TRIGGER_BUILDERS: dict[str, RuleTriggerBuilder] = {
    "R-VULN-GOODWILL-CAP": _trigger_goodwill_cap,
}


def parse_policy_annotations(policy_text: str) -> ParsedPolicyHeader:
    version = "unknown"
    rules: list[str] = []
    tools: list[str] = []

    for raw in policy_text.splitlines():
        line = raw.strip()
        if not line.startswith(";"):
            continue
        body = line[1:].strip()
        if body.startswith("Policy-Version:"):
            version = body.split(":", 1)[1].strip()
        elif body.startswith("Covers-Tool:"):
            t = body.split(":", 1)[1].strip()
            if t:
                tools.append(t)
        elif body.startswith("Rule-ID:"):
            rules.append(body.split(":", 1)[1].strip())

    return ParsedPolicyHeader(policy_version=version, rule_ids=rules, covered_tools=tools)


def _only_smt(policy_text: str) -> str:
    out_lines: list[str] = []
    for raw in policy_text.splitlines():
        stripped = raw.strip()
        if stripped.startswith(";"):
            continue
        out_lines.append(raw)
    return "\n".join(out_lines).strip() + "\n"


def build_consistency_report(
    policy_text: str,
    *,
    run_pairwise: bool = False,
) -> ConsistencyReport:
    """Pre-deploy checks per agentsim/03 (SAT, rule reachability, covered-tool coverage)."""

    from z3 import Bool, Not, Solver, parse_smt2_string, sat, unsat

    header = parse_policy_annotations(policy_text)
    smt_body = _only_smt(policy_text)

    report = ConsistencyReport(policy_version=header.policy_version, satisfiable=True)

    base = parse_smt2_string(smt_body)
    slv0 = Solver()
    for a in base:
        slv0.add(a)
    r0 = slv0.check()
    if r0 != sat:
        report.satisfiable = False
        explanation = "Policy assertions are not satisfiable (contradictory or inconsistent)."
        core_labels: list[str] = []
        if r0 == unsat:
            try:
                core_labels = [str(x) for x in slv0.unsat_core()]
            except Exception:  # noqa: BLE001
                pass
        report.contradictions.append(
            {"rule_ids": core_labels, "explanation": explanation},
        )
        return report

    if len(base) == 0:
        return report

    ctx = base[0].ctx

    legal_atom = Bool("sim-legal-goodwill", ctx)
    legal_exists = _atom_satisfiable_with_base(base, legal_atom)
    illegal_exists = _atom_satisfiable_with_base(base, Not(legal_atom))

    for rid in header.rule_ids:
        builder = RULE_TRIGGER_BUILDERS.get(rid)
        if builder is None:
            continue
        slv = Solver(ctx=ctx)
        for a in base:
            slv.add(a)
        slv.push()
        slv.add(builder(ctx))
        rr = slv.check()
        slv.pop()
        if rr != sat:
            report.unreachable_rules.append(rid)

    for tool in header.covered_tools:
        if tool == "apply_goodwill_credit":
            if not legal_exists:
                report.tools_always_illegal.append(tool)
            if not illegal_exists:
                report.tools_always_legal.append(tool)

    if run_pairwise and len(header.rule_ids) >= 2:
        _ = report, header

    return report


def _atom_satisfiable_with_base(base: list[Any], extra) -> bool:
    from z3 import Solver, sat

    ctx = base[0].ctx
    slv = Solver(ctx=ctx)
    for a in base:
        slv.add(a)
    slv.push()
    slv.add(extra)
    ok = slv.check() == sat
    slv.pop()
    return ok


def policy_text_from_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_report(path: Path, report: ConsistencyReport) -> None:
    path.write_text(report.to_json(), encoding="utf-8")


def deployment_should_fail(report: ConsistencyReport) -> bool:
    if not report.satisfiable:
        return True
    return len(report.contradictions) > 0
