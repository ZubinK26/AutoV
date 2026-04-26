"""
Interactive (or scripted) demo: ASP benchmark pools (paired NL + reference ASP) or manual input → WFM → registry.

Requires ASPBench clone under ``test_sets/datasets/aspbench/repo`` for option (1).
NL ASP-Bench requires ``test_sets/datasets/asp_nl_bench/installed.json`` pointing at official JSONL.

Run from repo root::

  python -m wfm_orchestration.demo_launcher
  python -m wfm_orchestration.demo_launcher --demo-choice aspbench --demo-seed 1 --dry-run
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from wfm_orchestration.asp_demo_sources import (
    AspNlBenchExample,
    SymTexPairedExample,
    asp_nl_bench_status,
    asp_nl_record_to_assessment_dict,
    compute_asp_manual_word_limit,
    load_asp_nl_bench_index,
    load_symtex_paired_index,
    pick_asp_nl_example,
    pick_symtex_example,
    symtex_clone_present,
    symtex_record_to_assessment_dict,
    write_wfm_asp_assessment,
)
from wfm_orchestration.ground_truth_asp import truth_assessment_manual
from wfm_orchestration.cli import run_e2e
from wfm_orchestration.e2e_context import load_dotenv_for_e2e
from wfm_orchestration.demo_loader import ManualInputRejected, validate_manual_text, word_count
from wfm_orchestration.handoff_artifacts import handoff_write_path

_symtex_cache: list[SymTexPairedExample] | None = None
_asp_nl_cache: list[AspNlBenchExample] | None = None


def _symtex_index(repo_root: Path) -> list[SymTexPairedExample]:
    global _symtex_cache
    if _symtex_cache is None:
        _symtex_cache = load_symtex_paired_index(repo_root)
    return _symtex_cache


def _asp_nl_index(repo_root: Path) -> list[AspNlBenchExample]:
    global _asp_nl_cache
    if _asp_nl_cache is None:
        _asp_nl_cache = load_asp_nl_bench_index(repo_root)
    return _asp_nl_cache


def _default_warm_registry_path() -> Path:
    return _REPO / "exports" / "wfm_demo_warm_registry.json"


def _build_warm_session(path: Path, *, persist_load: bool, clear_existing: bool):
    from registry_stage.loaders import load_registry
    from registry_stage.registry_session import RegistrySession
    from registry_stage.semantic_index import StubKeywordSemanticIndex

    session = RegistrySession(semantic_index=StubKeywordSemanticIndex(), index_preference="stub")
    if clear_existing:
        if path.is_file():
            path.unlink()
        return session
    if persist_load and path.is_file():
        reg = load_registry(path)
        for e in reg.entries:
            session.add_or_replace(e)
    return session


def _ask_yes_no(prompt: str, input_fn: Callable[[str], str]) -> bool:
    while True:
        line = input_fn(prompt).strip().lower()
        if line in ("y", "yes"):
            return True
        if line in ("n", "no", ""):
            return False
        print("  Please enter y or n.", file=sys.stderr)


def _interactive_warm_registry_prompts(input_fn: Callable[[str], str]) -> tuple[bool, bool, Path]:
    path = _default_warm_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    print()
    q1 = _ask_yes_no(
        "Load persisted demo registry from the last run (if any) and save this run's registry when done? [y/N]: ",
        input_fn,
    )
    q2 = _ask_yes_no(
        "Clear all entities from the persisted demo registry file now (before this run)? [y/N]: ",
        input_fn,
    )
    return q1, q2, path


def _apply_warm_registry_to_args(
    args: argparse.Namespace,
    *,
    persist_load: bool,
    clear_existing: bool,
    path: Path,
) -> None:
    session = _build_warm_session(path, persist_load=persist_load, clear_existing=clear_existing)
    args._registry_session_override = session
    args.persist_registry_after_run = persist_load
    args.persist_registry_path = path


def _scripted_warm_registry(args: argparse.Namespace) -> None:
    path = _default_warm_registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    warm = bool(getattr(args, "warm_registry", False))
    clear = bool(getattr(args, "clear_warm_registry", False))
    if warm:
        session = _build_warm_session(path, persist_load=True, clear_existing=clear)
        persist_after = True
    else:
        session = _build_warm_session(path, persist_load=False, clear_existing=clear)
        persist_after = False
    args._registry_session_override = session
    args.persist_registry_after_run = persist_after
    args.persist_registry_path = path


def _print_input_rule_banner(initial: str, ex_id: str | None) -> None:
    label = f"example {ex_id}" if ex_id else "manual input"
    print()
    print("=" * 72)
    print(f"  Rule text for WFM ({label})")
    print("=" * 72)
    print(initial)
    print("=" * 72)
    print()


def _read_manual_multiline(
    *,
    limit: int,
    input_fn: Callable[[str], str] = input,
) -> str:
    print(f"Manual input (max {limit} words). Enter lines; finish with a blank line.")
    lines: list[str] = []
    while True:
        line = input_fn()
        if line == "":
            break
        lines.append(line)
    text = "\n".join(lines).strip()
    if not text:
        raise ValueError("empty manual input")
    validate_manual_text(text, limit=limit)
    return text


def _manual_word_cap(repo_root: Path) -> int:
    try:
        idx = _symtex_index(repo_root)
        return compute_asp_manual_word_limit(idx)
    except (FileNotFoundError, RuntimeError):
        pass
    try:
        nidx = _asp_nl_index(repo_root)
        m = max(len(x.nl_document.split()) for x in nidx)
        return m + 40
    except (FileNotFoundError, RuntimeError):
        return 2500


def _interactive_confirm_symtex(
    *,
    repo_root: Path,
    rng: random.Random,
    input_fn: Callable[[str], str],
) -> tuple[str, str, dict[str, Any]]:
    idx = _symtex_index(repo_root)
    exclude: set[str] = set()
    while True:
        ex = pick_symtex_example(idx, rng=rng, exclude_ids=exclude)
        _print_input_rule_banner(ex.nl_document, ex.manifest_example_id)
        print(f"(SymTex task: {ex.task}; source id: {ex.source_id})\n")
        if _ask_yes_no("Use this example for WFM? [y/N]: ", input_fn):
            return ex.nl_document, ex.manifest_example_id, symtex_record_to_assessment_dict(ex)
        exclude.add(ex.manifest_example_id)
        print("(Picking another SymTex instance.)\n")


def _interactive_confirm_asp_nl(
    *,
    repo_root: Path,
    rng: random.Random,
    input_fn: Callable[[str], str],
) -> tuple[str, str, dict[str, Any]]:
    idx = _asp_nl_index(repo_root)
    exclude: set[str] = set()
    while True:
        ex = pick_asp_nl_example(idx, rng=rng, exclude_ids=exclude)
        eid = f"ASPNL-{ex.source_id}"[:240]
        _print_input_rule_banner(ex.nl_document, eid)
        if _ask_yes_no("Use this example for WFM? [y/N]: ", input_fn):
            return ex.nl_document, eid, asp_nl_record_to_assessment_dict(ex)
        exclude.add(ex.source_id)
        print("(Picking another NL ASP-Bench instance.)\n")


def _interactive_pick(
    *,
    repo_root: Path,
    rng: random.Random,
    input_fn: Callable[[str], str],
) -> tuple[str, str | None, bool, dict[str, Any] | None]:
    """
    Returns ``(initial_text, example_id_or_none, skip_rule_banner, assessment_dataset_or_none)``.
    """
    limit = _manual_word_cap(repo_root)
    symtex_ok = symtex_clone_present(repo_root)
    nl_ok, nl_msg = asp_nl_bench_status(repo_root)

    while True:
        print("\nWFM demo — ASP evaluation pools (paired NL + reference ASP from each source).\n")
        print(
            "  1) ASPBench SymTex (HomuraT/ASPBench — paired NL + reference ASP on disk; see aspbench/README.md)\n"
            f"      {'[available]' if symtex_ok else '[MISSING clone — see test_sets/datasets/aspbench/README.md]'}\n"
            "  2) NL ASP-Bench (arXiv:2602.01171) via installed.json — only rows with reference LP in your JSONL\n"
            f"      {'[available]' if nl_ok else '[not installed]'}\n"
            "  3) Manual input (no in-repo reference; not for automatic truth scoring)\n"
            "  4) Quit\n"
        )
        if not nl_ok:
            print(f"  Note (2): {nl_msg}\n")

        choice = input_fn("Select 1–4: ").strip()

        if choice == "1":
            if not symtex_ok:
                print(
                    "\nASPBench SymTex is not on disk. Clone into the repo, then try again:\n"
                    "  git clone https://github.com/HomuraT/ASPBench.git test_sets/datasets/aspbench/repo\n",
                    file=sys.stderr,
                )
                continue
            body, ex_id, rec = _interactive_confirm_symtex(repo_root=repo_root, rng=rng, input_fn=input_fn)
            return body, ex_id, True, rec
        if choice == "2":
            if not nl_ok:
                print(f"\n{nl_msg}\n", file=sys.stderr)
                print("(Choose 1, 3, or 4 — or add installed.json and restart.)\n")
                continue
            body, ex_id, rec = _interactive_confirm_asp_nl(repo_root=repo_root, rng=rng, input_fn=input_fn)
            return body, ex_id, True, rec
        if choice == "3":
            text = _read_manual_multiline(limit=limit, input_fn=input_fn)
            manual_dataset = {
                "source": "manual",
                "truth_assessment": truth_assessment_manual(),
            }
            return text, None, False, manual_dataset
        if choice == "4":
            raise SystemExit(0)
        print(f"Invalid choice: {choice!r}. Enter 1–4.\n", file=sys.stderr)


def _resolve_initial_text_scripted(
    args: argparse.Namespace,
    *,
    rng: random.Random,
    repo_root: Path,
) -> tuple[str, str | None, dict[str, Any] | None]:
    limit = _manual_word_cap(repo_root)
    if args.demo_choice == "manual":
        if args.file is not None:
            initial = args.file.read_text(encoding="utf-8").strip()
        else:
            initial = args.text.strip()
        if not initial:
            raise SystemExit("error: --demo-choice manual requires --text or --file")
        validate_manual_text(initial, limit=limit)
        return initial, None, {
            "source": "manual",
            "truth_assessment": truth_assessment_manual(),
        }

    if args.demo_choice == "aspbench":
        idx = _symtex_index(repo_root)
        ex = pick_symtex_example(idx, rng=rng)
        return (
            ex.nl_document,
            ex.manifest_example_id,
            symtex_record_to_assessment_dict(ex),
        )

    if args.demo_choice == "asp_nl_bench":
        idx = _asp_nl_index(repo_root)
        ex = pick_asp_nl_example(idx, rng=rng)
        eid = f"ASPNL-{ex.source_id}"[:240]
        return ex.nl_document, eid, asp_nl_record_to_assessment_dict(ex)

    raise SystemExit(f"unknown --demo-choice: {args.demo_choice!r}")


def _maybe_write_assessment(
    args: argparse.Namespace,
    *,
    repo_root: Path,
    rc: int,
) -> None:
    if rc != 0:
        return
    dataset = getattr(args, "_asp_assessment_dataset", None)
    if not isinstance(dataset, dict):
        return
    sess = getattr(args, "_last_dev_session", None)
    bundle_id: str | None = None
    if sess is not None and sess.bundle is not None:
        bundle_id = sess.bundle.bundle_id
    if not bundle_id:
        return
    hp: Path | None = None
    if getattr(args, "handoff", None):
        hp = Path(args.handoff)
    elif not args.no_handoff_save:
        hp = handoff_write_path(repo_root, bundle_id, handoff_dir=getattr(args, "handoff_dir", None))
    notes = getattr(sess, "notes", None) if sess is not None else None
    out = write_wfm_asp_assessment(
        repo_root=repo_root,
        bundle_id=bundle_id,
        handoff_path=hp,
        dataset_record=dataset,
        dev_session_notes=notes,
    )
    print(f"\n[Demo] Wrote assessment JSON (NL + reference ASP + bundle id): {out.resolve()}\n")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="WFM → registry e2e with ASP benchmark demo pools.")
    p.add_argument(
        "--demo-choice",
        choices=("aspbench", "asp_nl_bench", "manual"),
        default=None,
        help="Skip menu: aspbench | asp_nl_bench | manual.",
    )
    p.add_argument(
        "--demo-seed",
        type=int,
        default=None,
        help="Seed for random benchmark pick (ignored for manual).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print chosen example / word counts and exit (no Gemini).",
    )
    p.add_argument("--text", type=str, default="", help="Initial rule text (with --demo-choice manual).")
    p.add_argument("--file", type=Path, default=None, help="UTF-8 file with initial text.")
    p.add_argument("--export", type=Path, default=None, help="Write DevSessionSnapshot JSON after registry.")
    p.add_argument("--handoff", type=Path, default=None, help="Explicit HandoffBundle JSON path (overrides default dir).")
    p.add_argument(
        "--handoff-dir",
        type=Path,
        default=None,
        help="Directory for HandoffBundle JSON (default: bundles/wfm_artifacts).",
    )
    p.add_argument(
        "--no-handoff-save",
        action="store_true",
        help="Do not auto-save handoff under bundles/wfm_artifacts.",
    )
    p.add_argument(
        "--example-id",
        type=str,
        default=None,
        help="Override manifest example id (benchmark runs set this from the pick when omitted).",
    )
    p.add_argument(
        "--auto-accept",
        action="store_true",
        help="Accept confirmation without prompting.",
    )
    p.add_argument(
        "--skip-registry",
        action="store_true",
        help="Stop after handoff JSON (no M4 / registry).",
    )
    p.add_argument("--mock-resolve", action="store_true", help="Stub M4 resolver JSON (no Gemini for M4).")
    p.add_argument("--bundle-id", type=str, default=None, help="Override generated bundle_id (G3).")
    p.add_argument("--bundle-prefix", type=str, default="demo", help="Prefix when bundle_id is auto-generated.")
    p.add_argument(
        "--no-artifacts",
        action="store_true",
        help="Skip automatic exports/e2e_demo_runs/<timestamp>_<id>/ (dev_session.json + G8 viewer).",
    )
    p.add_argument(
        "--warm-registry",
        action="store_true",
        help="With --demo-choice: load exports/wfm_demo_warm_registry.json if present and save after success.",
    )
    p.add_argument(
        "--clear-warm-registry",
        action="store_true",
        help="Delete warm registry file before run (empty start); combine with --warm-registry to save a fresh registry after.",
    )
    p.add_argument(
        "--formalize-asp",
        action="store_true",
        help="After WFM, run ClinCon/Clingo (parse/ground, identifier critic) and write policy .lp + bundle record.",
    )
    p.add_argument(
        "--asp-policy",
        type=Path,
        default=None,
        help="Output .lp (default: bundles/asp_from_wfm/policies/<bundle_id>.lp).",
    )
    p.add_argument(
        "--asp-bundle-out",
        type=Path,
        default=None,
        help="ASP bundle sidecar directory (default: bundles/asp_from_wfm).",
    )
    p.add_argument(
        "--asp-formalizer-prompt",
        type=str,
        default=None,
        help="Basename of formalizer under asp_pipeline/prompts/ (default: formalizer_new.md).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    repo_root = _REPO

    if args.demo_seed is not None and args.demo_choice == "manual":
        print("warning: --demo-seed does not apply to manual input; ignoring.", file=sys.stderr)

    rng = random.Random(args.demo_seed)

    if args.demo_choice is None:
        q1, q2, wpath = _interactive_warm_registry_prompts(input)
        _apply_warm_registry_to_args(args, persist_load=q1, clear_existing=q2, path=wpath)
        try:
            initial, ex_id, skip_rule_banner, assessment_ds = _interactive_pick(
                repo_root=repo_root, rng=rng, input_fn=input
            )
        except ManualInputRejected as e:
            print(f"error: {e.word_count} words exceeds manual cap {e.limit}.", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    else:
        _scripted_warm_registry(args)
        skip_rule_banner = False
        try:
            initial, ex_id, assessment_ds = _resolve_initial_text_scripted(args, rng=rng, repo_root=repo_root)
        except ManualInputRejected as e:
            print(f"error: {e.word_count} words exceeds manual cap {e.limit}.", file=sys.stderr)
            return 2

    args._asp_assessment_dataset = assessment_ds

    if not skip_rule_banner:
        _print_input_rule_banner(initial, ex_id)

    if ex_id is not None and getattr(args, "example_id", None) is None:
        args.example_id = ex_id

    if args.dry_run:
        wc = word_count(initial)
        print(f"manual_word_cap (approx) = {_manual_word_cap(repo_root)} (from SymTex / NL-Bench or default)")
        if ex_id:
            print(f"example_id: {ex_id}")
        print(f"word_count: {wc}")
        if assessment_ds:
            print("assessment dataset keys:", ", ".join(sorted(assessment_ds.keys())))
        print("(dry-run - no WFM)")
        return 0

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

    if ex_id:
        print(f"[Demo] Starting WFM — {ex_id}\n")
    else:
        print("[Demo] Starting WFM — manual input (no reference ASP record).\n")

    rc = run_e2e(args, initial)
    _maybe_write_assessment(args, repo_root=repo_root, rc=rc)
    if rc == 0 and getattr(args, "formalize_asp", False):
        from asp_pipeline.wfm_hook import run_asp_formalize_after_wfm

        return run_asp_formalize_after_wfm(
            session=getattr(args, "_last_dev_session", None),
            args=args,
            repo_root=repo_root,
        )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
