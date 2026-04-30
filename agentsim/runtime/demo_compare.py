from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agentsim.runtime.comparison import compare_vanilla_vs_gated
from agentsim.runtime.harness import ScenarioHarness
from agentsim.runtime.scenario_runner import load_scenarios_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Slice E demo: vanilla vs gated metrics per scripted scenario (agentsim/02–03).",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=None,
        help="Path to scenarios JSON array (default: bundled agentsim scenarios.json)",
    )
    args = parser.parse_args(argv)

    if args.scenarios is not None:
        scenarios: list[dict[str, Any]] = json.loads(args.scenarios.read_text(encoding="utf-8"))
    else:
        scenarios = load_scenarios_bundle()

    rows = []
    for sc in scenarios:
        cid = sc["customer_id"]

        def make_vanilla(cid: str = cid) -> Any:
            return ScenarioHarness(policy_version="demo-vanilla").begin_scenario_always_allow_full_snapshots(
                customer_id=cid,
            )

        def make_gated(cid: str = cid) -> Any:
            return ScenarioHarness(policy_version="policy-v0").begin_scenario(
                customer_id=cid,
                use_builtin_z3_policy=True,
            )

        m = compare_vanilla_vs_gated(make_vanilla, make_gated, sc)
        rows.append(
            {
                "scenario": m.scenario_id,
                "domain": sc.get("domain", ""),
                "writes": m.write_steps,
                "vanilla_posthoc_blocks": m.vanilla_would_block_posthoc,
                "gated_live_blocks": m.gated_live_blocks,
                "gated_allows": m.gated_writes_allowed,
                "force_escalation_events": m.gated_force_escalation_events,
            },
        )

    print(json.dumps(rows, indent=2))
    total_vanilla = sum(r["vanilla_posthoc_blocks"] for r in rows)
    total_gated = sum(r["gated_live_blocks"] for r in rows)
    print(
        f"\n# Summary: vanilla_posthoc_blocks={total_vanilla} gated_live_blocks={total_gated} "
        f"(scenarios={len(rows)})",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
