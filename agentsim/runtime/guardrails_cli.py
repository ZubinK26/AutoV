"""CLI: verify grounded scenarios against ``policy_model_refined.smt2``."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from pathlib import Path

from agentsim.runtime.guardrails_checker import (
    GuardrailsPolicyChecker,
    default_guardrails_policy_path,
)
from agentsim.runtime.guardrails_scenario import GuardrailsScenario


def _scenario_from_json(data: object) -> GuardrailsScenario:
    if not isinstance(data, dict):
        msg = "scenario JSON must be an object"
        raise ValueError(msg)
    allowed = {f.name for f in fields(GuardrailsScenario)}
    kwargs = {k: v for k, v in data.items() if k in allowed}
    return GuardrailsScenario(**kwargs)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Check GuardrailsScenario slices against policy_model_refined.smt2 (Z3 entailment)."
        ),
    )
    p.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Path to policy .smt2 (default: exports/.../policy_model_refined.smt2)",
    )
    p.add_argument(
        "--scenario",
        type=Path,
        default=None,
        help="JSON object with GuardrailsScenario fields (prints one verdict line)",
    )
    p.add_argument(
        "--demo",
        action="store_true",
        help="Run built-in demo scenarios and print JSON lines",
    )
    args = p.parse_args(argv)

    policy_path = args.policy
    if policy_path is None:
        policy_path = default_guardrails_policy_path()

    if not policy_path.is_file():
        sys.stderr.write(f"Policy file not found: {policy_path}\n")
        return 2

    if args.scenario:
        data = json.loads(args.scenario.read_text(encoding="utf-8"))
        scen = _scenario_from_json(data)
        checker = GuardrailsPolicyChecker(policy_path=policy_path)
        d = checker.decide(scen)
        print(json.dumps(d.to_dict(), indent=2))
        return 0

    if args.demo:
        checker = GuardrailsPolicyChecker(policy_path=policy_path)
        demos = [
            (
                "escalate_allows",
                GuardrailsScenario(primary_tool="escalate"),
            ),
            (
                "missing_entity_denies",
                GuardrailsScenario(
                    primary_tool="apply_refund",
                    references_missing_entity=True,
                ),
            ),
            (
                "duplicate_prior_denies",
                GuardrailsScenario(
                    primary_tool="apply_refund",
                    duplicate_prior_allowed=True,
                ),
            ),
            (
                "closed_account_freeze_denies",
                GuardrailsScenario(
                    primary_tool="freeze_card",
                    account_status="CLOSED",
                ),
            ),
        ]
        for name, scen in demos:
            d = checker.decide(scen)
            print(json.dumps({"case": name, **d.to_dict()}))
        return 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
