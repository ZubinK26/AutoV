"""CLI entry to run the cross-coherence slice on an existing work directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=(
            "Run CrossCritic (and optionally CrossRepairer) on an existing pivot run: "
            "uses work_dir phase0_normalized_nl.txt when present, else --input; "
            "loads rules from --rules-json (default: <work-dir>/rules_extracted.json)."
        )
    )
    p.add_argument("--work-dir", required=True, type=Path)
    p.add_argument("--input", required=True, type=Path, help="policy_id source (stem); same resolution as pivot_pipeline CLI")
    p.add_argument(
        "--rules-json",
        type=Path,
        default=None,
        help="Defaults to <work-dir>/rules_extracted.json",
    )
    p.add_argument("--repo-root", type=Path, default=_REPO)
    p.add_argument(
        "--skip-semantic-critic",
        action="store_true",
        help="Skip pivot_critic before cross slice; use with --cross-coherence-skip-critic-gate",
    )
    p.add_argument("--with-cross-repair", action="store_true")
    p.add_argument("--interactive-policy", action="store_true")
    p.add_argument("--interactive-cross-coherence", action="store_true")
    p.add_argument("--cross-coherence-skip-critic-gate", action="store_true")
    p.add_argument("--fail-on-precheck-warnings", action="store_true")
    p.add_argument("--fail-on-varprod-trigger", action="store_true")
    p.add_argument("--no-llm", action="store_true")
    p.add_argument("--skip-registry", action="store_true")
    args = p.parse_args(argv)

    rules_json = args.rules_json or (args.work_dir / "rules_extracted.json")
    if not rules_json.is_file():
        print(f"rules JSON not found: {rules_json}", file=sys.stderr)
        return 1

    from pivot_pipeline.paths import resolve_existing_user_file
    from pivot_pipeline.run import run_pivot_pipeline

    nl_source = resolve_existing_user_file(args.input)

    summary = run_pivot_pipeline(
        repo_root=args.repo_root.resolve(),
        work_dir=args.work_dir,
        nl_source=nl_source,
        rules_json=rules_json,
        skip_phase0=True,
        reset_progress=False,
        rules_per_chunk=5,
        skip_critic=args.skip_semantic_critic,
        no_llm=args.no_llm,
        skip_registry=args.skip_registry,
        extract_only=False,
        interactive_policy=args.interactive_policy,
        interactive_extract_abort=False,
        interactive_cross_coherence=args.interactive_cross_coherence,
        with_tester=False,
        fail_on_tester_findings=False,
        repairer_max_rounds=2,
        with_cross_critic=True,
        with_cross_repair=args.with_cross_repair,
        cross_coherence_skip_critic_gate=args.cross_coherence_skip_critic_gate,
        fail_on_precheck_warnings=args.fail_on_precheck_warnings,
        fail_on_varprod_trigger=args.fail_on_varprod_trigger,
        input_fn=input,
        print_fn=print,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    outcome = summary.get("outcome", "")
    if outcome.startswith("blocked"):
        return (
            1
            if outcome not in ("blocked_critic", "blocked_semantic_repair_compile")
            else 3
        )
    if summary.get("precheck_ok") is False:
        return 2
    if summary.get("varprod_trigger_ok") is False:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
