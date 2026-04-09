"""M6 — runnable registry-stage harness (`python -m registry_stage.run`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from registry_stage.bundle_workflow import registry_session_to_registry_file, run_bundle_through_registry
from registry_stage.export_session import export_session
from registry_stage.line_driver import LineDriverConfig
from registry_stage.loaders import load_handoff_bundle, load_registry, save_registry
from registry_stage.models import SCHEMA_VERSION, RegistryFile
from registry_stage.registry_session import RegistrySession
from registry_stage.semantic_index import StubKeywordSemanticIndex


def _default_bundle_path() -> Path:
    return Path.cwd() / "bundles" / "fixture_bu_001.json"


def _session_for_cli(*, index: str) -> RegistrySession:
    if index == "stub":
        return RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    return RegistrySession(index_preference="faiss")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Registry stage Phase 1 — bundle → search → resolve → populate → export.")
    p.add_argument(
        "--bundle",
        type=Path,
        default=None,
        help="Handoff JSON path (default: ./bundles/fixture_bu_001.json under cwd)",
    )
    p.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Optional registry JSON to load as warm start (missing file → empty shell)",
    )
    p.add_argument(
        "--export",
        type=Path,
        default=None,
        help="Write dev session snapshot JSON (registry + handoff + line_traces)",
    )
    p.add_argument(
        "--save-registry",
        type=Path,
        default=None,
        help="Write registry JSON only after run (for next warm start)",
    )
    p.add_argument(
        "--index",
        choices=("stub", "faiss"),
        default="faiss",
        help="Semantic index backend (stub for fast local smoke without BGE/FAISS)",
    )
    p.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable M3 Gemini expansion/extraction (heuristic gaps only). **Resolve (M4) still calls Gemini** — use tests with "
        "mocked ``llm_complete`` for fully offline runs, or set ``GEMINI_API_KEY`` for a live demo.",
    )
    args = p.parse_args(argv)

    bundle_path = args.bundle or _default_bundle_path()
    if not bundle_path.is_file():
        print(f"error: bundle not found: {bundle_path}", file=sys.stderr)
        return 2

    bundle = load_handoff_bundle(bundle_path)
    if args.registry is not None:
        reg = load_registry(args.registry)
    else:
        reg = RegistryFile(schema_version=SCHEMA_VERSION, entries=[], entry_edges=[])
    session = _session_for_cli(index=args.index)
    for ent in reg.entries:
        session.add_or_replace(ent)

    if args.no_llm:
        line_cfg = LineDriverConfig(enable_llm=False)
    else:
        line_cfg = LineDriverConfig(
            enable_llm=True,
            query_mode="single_concat",
            masking_preset="conservative",
        )

    def llm_complete(system: str, user: str) -> str:
        from registry_stage.llm.gemini_call import gemini_complete

        return gemini_complete(system_instruction=system, user_text=user)

    try:
        snapshot = run_bundle_through_registry(
            bundle,
            session,
            llm_complete=llm_complete,
            line_config=line_cfg,
        )
    except Exception as exc:
        print(f"error: pipeline failed: {exc}", file=sys.stderr)
        return 1

    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        export_session(args.export, snapshot)

    if args.save_registry:
        args.save_registry.parent.mkdir(parents=True, exist_ok=True)
        save_registry(args.save_registry, registry_session_to_registry_file(session))

    for tr in snapshot.line_traces:
        li = tr.get("line_index")
        st = tr.get("statement_nl", "")[:72]
        verdict = tr.get("validation_outcome") or tr.get("skipped_reason")
        rn = tr.get("registry_resolved_nl")
        print(f"line {li}: {verdict} — {st!r}…")
        if rn:
            print(f"  registry_resolved_nl: {rn!r}")
        elif tr.get("failure_reasons"):
            print(f"  failure_reasons: {tr['failure_reasons']!r}")

    summary = {
        "bundle_id": bundle.bundle_id,
        "lines": len(snapshot.line_traces),
        "registry_entry_count": len(snapshot.registry.entries) if snapshot.registry else 0,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
