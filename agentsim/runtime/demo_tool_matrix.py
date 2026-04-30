"""CLI: run all write-tool probes (one fresh DB per tool) and print JSONL verdicts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentsim.runtime.simulation_batch import run_write_tool_matrix


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate one agent write per tool with DB-backed snapshots and policy validation. "
            "Use --policy to point at SMT-LIB from the WFM formalization pipeline (defaults to bundled v0)."
        ),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Path to policy .smt2 (optional; default bundled policy_v0.smt2)",
    )
    parser.add_argument(
        "--no-z3",
        action="store_true",
        help="Skip Z3 policy; always-allow writes (smoke-test DB and tool wiring only)",
    )
    parser.add_argument(
        "--customer-id",
        default="C-001",
        help="Seed customer for the interaction (default C-001)",
    )
    args = parser.parse_args()

    records = run_write_tool_matrix(
        customer_id=args.customer_id,
        use_builtin_z3_policy=not args.no_z3,
        policy_smt2_path=args.policy,
    )
    for r in records:
        print(json.dumps(r.to_json_dict(), sort_keys=True))


if __name__ == "__main__":
    main()
