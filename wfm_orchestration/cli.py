"""CLI: WFM to registry e2e (Gemini). Run from repo root: ``python -m wfm_orchestration.cli``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Repo root on path
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from wfm_orchestration.e2e_context import create_e2e_context, load_dotenv_for_e2e
from wfm_orchestration.orchestrator import run_wfm_registry_e2e


def run_e2e(args: argparse.Namespace, initial_user_text: str) -> int:
    """Shared entry for ``cli`` and ``demo_launcher`` (G6/G7)."""
    override = getattr(args, "_registry_session_override", None)
    ctx = create_e2e_context(mock_resolve=args.mock_resolve, registry_session=override)
    out = run_wfm_registry_e2e(
        initial_user_text=initial_user_text,
        client=ctx.client,
        model=ctx.model,
        temperature=ctx.temperature,
        max_output_tokens=ctx.max_output_tokens,
        thinking_level=ctx.thinking_level,
        registry_session=ctx.registry_session,
        llm_complete=ctx.llm_complete,
        bundle_id=args.bundle_id,
        bundle_id_prefix=args.bundle_prefix,
        export_json=args.export,
        handoff_json=args.handoff,
        repo_root=_REPO,
        handoff_dir=getattr(args, "handoff_dir", None),
        persist_handoff=not args.no_handoff_save,
        example_id=getattr(args, "example_id", None),
        auto_accept=getattr(args, "auto_accept", False),
        skip_registry=getattr(args, "skip_registry", False),
        provider_model=ctx.model,
        auto_artifacts=not args.no_artifacts,
    )
    if out is not None and getattr(args, "persist_registry_after_run", False):
        p = getattr(args, "persist_registry_path", None)
        if p is not None:
            from registry_stage.bundle_workflow import registry_session_to_registry_file
            from registry_stage.loaders import save_registry

            p = Path(p)
            p.parent.mkdir(parents=True, exist_ok=True)
            save_registry(p, registry_session_to_registry_file(ctx.registry_session))
            print(f"Saved warm registry for next demo: {p.resolve()}")
    setattr(args, "_last_dev_session", out)
    return 0 if out is not None else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="WFM Agents 1-3 (+4) to HandoffBundle to registry stage (Phase 1)."
    )
    p.add_argument(
        "--text",
        type=str,
        default="",
        help="Initial user NL rule (WFM input). If empty, read from --file.",
    )
    p.add_argument("--file", type=Path, default=None, help="UTF-8 file with initial user text.")
    p.add_argument("--export", type=Path, default=None, help="Write DevSessionSnapshot JSON after registry.")
    p.add_argument("--handoff", type=Path, default=None, help="Explicit HandoffBundle JSON path (overrides default dir).")
    p.add_argument(
        "--handoff-dir",
        type=Path,
        default=None,
        help="Directory for HandoffBundle JSON (default: bundles/wfm_artifacts under repo root).",
    )
    p.add_argument(
        "--no-handoff-save",
        action="store_true",
        help="Do not write bundles/wfm_artifacts/<bundle_id>.json or manifest line.",
    )
    p.add_argument(
        "--example-id",
        type=str,
        default=None,
        help="Label for manifest.jsonl (e.g. curated F-8), optional.",
    )
    p.add_argument(
        "--auto-accept",
        action="store_true",
        help="Accept confirmation without prompting (for scripted / batch runs).",
    )
    p.add_argument(
        "--skip-registry",
        action="store_true",
        help="Stop after handoff JSON (no M4 / registry); for smt_pipeline-only evaluation.",
    )
    p.add_argument(
        "--mock-resolve",
        action="store_true",
        help="Use a stub resolver JSON (no GEMINI for M4), for dry integration tests.",
    )
    p.add_argument(
        "--bundle-id",
        type=str,
        default=None,
        help="Override generated bundle_id (default: demo_<UTC>_<hex> per G3).",
    )
    p.add_argument(
        "--bundle-prefix",
        type=str,
        default="demo",
        help="Prefix when bundle_id is auto-generated (G3).",
    )
    p.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Skip automatic exports/e2e_demo_runs/<timestamp>_<id>/ (dev_session.json + G8 viewer).",
    )
    p.add_argument(
        "--formalize-asp",
        action="store_true",
        help="After WFM, run ClinCon/Clingo pipeline (Clingo parse/ground, critic) on the handoff.",
    )
    p.add_argument(
        "--asp-policy",
        type=Path,
        default=None,
        help="Output .lp path (default: bundles/asp_from_wfm/policies/<bundle_id>.lp).",
    )
    p.add_argument(
        "--asp-bundle-out",
        type=Path,
        default=None,
        help="ASP bundle records dir (default: bundles/asp_from_wfm).",
    )
    p.add_argument(
        "--asp-formalizer-prompt",
        type=str,
        default=None,
        help="Basename of formalizer under asp_pipeline/prompts/ (default: formalizer_new.md).",
    )
    args = p.parse_args(argv)

    if args.file is not None:
        initial = args.file.read_text(encoding="utf-8")
    else:
        initial = args.text.strip()
    if not initial:
        print("error: provide --text or --file", file=sys.stderr)
        return 2

    load_dotenv_for_e2e()
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("error: set GEMINI_API_KEY for WFM (Agents 1–4)", file=sys.stderr)
        return 2

    try:
        from google import genai  # noqa: F401
    except ImportError:
        print("error: pip install -r test_sets/requirements-wfm-test.txt", file=sys.stderr)
        return 2

    rc0 = run_e2e(args, initial)
    if not getattr(args, "formalize_asp", False) or rc0 != 0:
        return rc0
    from asp_pipeline.wfm_hook import run_asp_formalize_after_wfm

    return run_asp_formalize_after_wfm(session=getattr(args, "_last_dev_session", None), args=args, repo_root=_REPO)


if __name__ == "__main__":
    raise SystemExit(main())
