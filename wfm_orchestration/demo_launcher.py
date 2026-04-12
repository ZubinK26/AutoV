"""
Interactive (or scripted) demo: curated FOLIO / P-FOLIO / stress or manual input → same e2e as ``cli`` (**G6 / G7**).

Run from repo root::

  python -m wfm_orchestration.demo_launcher
  python -m wfm_orchestration.demo_launcher --demo-choice folio --demo-seed 1 --dry-run
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

from wfm_orchestration.cli import run_e2e
from wfm_orchestration.e2e_context import load_dotenv_for_e2e
from wfm_orchestration.demo_loader import (
    ManualInputRejected,
    compute_manual_word_limit,
    load_demo_pool_config,
    text_for_demo_choice,
    validate_manual_text,
    word_count,
)


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


def _interactive_confirm_curated_pool(
    pool: str,
    *,
    cfg: dict[str, Any],
    rng: random.Random,
    input_fn: Callable[[str], str],
) -> tuple[str, str]:
    """Random pick from pool; show text; repeat until user confirms (re-picks exclude rejected ids)."""
    exclude: set[str] = set()
    while True:
        ex_id, body = text_for_demo_choice(pool, cfg=cfg, rng=rng, exclude_ids=exclude)
        _print_input_rule_banner(body, ex_id)
        if _ask_yes_no("Use this example for WFM? [y/N]: ", input_fn):
            return body, ex_id
        exclude.add(ex_id)
        print("(Picking another example from the same pool.)\n")


def _print_input_rule_banner(initial: str, ex_id: str | None) -> None:
    """Show the rule text before WFM so Agent 2/3 output is not context-free."""
    label = f"curated example {ex_id}" if ex_id else "manual input"
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


def _resolve_initial_text(
    args: argparse.Namespace,
    *,
    rng: random.Random,
    cfg: dict,
) -> tuple[str, str | None]:
    """
    Returns ``(initial_user_text, example_id_or_none)``.
    """
    limit = compute_manual_word_limit(cfg)
    if args.demo_choice == "manual":
        if args.file is not None:
            initial = args.file.read_text(encoding="utf-8").strip()
        else:
            initial = args.text.strip()
        if not initial:
            raise SystemExit("error: --demo-choice manual requires --text or --file")
        validate_manual_text(initial, limit=limit)
        return initial, None

    ex_id, body = text_for_demo_choice(args.demo_choice, cfg=cfg, rng=rng)
    return body, ex_id


def _interactive_pick(
    *,
    limit: int,
    cfg: dict[str, Any],
    rng: random.Random,
    input_fn: Callable[[str], str] = input,
) -> tuple[str, str | None, bool]:
    """
    Returns ``(initial_text, example_id_or_none, skip_rule_banner_in_main)``.
    Curated picks (1–3) confirm in-loop and set ``skip_rule_banner_in_main`` True to avoid duplicating the banner.
    """
    print(
        "\nDemo input (G6 curated pools; manual cap G7 = max curated words + 15):\n"
        "  1) P-FOLIO — random curated example\n"
        "  2) FOLIO — random curated example\n"
        "  3) Stress — random curated example\n"
        "  4) Manual (subject to word cap)\n"
        "  5) Quit\n"
    )
    choice = input_fn("Select 1–5: ").strip()

    if choice == "1":
        body, ex_id = _interactive_confirm_curated_pool("pfolio", cfg=cfg, rng=rng, input_fn=input_fn)
        return body, ex_id, True
    if choice == "2":
        body, ex_id = _interactive_confirm_curated_pool("folio", cfg=cfg, rng=rng, input_fn=input_fn)
        return body, ex_id, True
    if choice == "3":
        body, ex_id = _interactive_confirm_curated_pool("stress", cfg=cfg, rng=rng, input_fn=input_fn)
        return body, ex_id, True
    if choice == "4":
        text = _read_manual_multiline(limit=limit, input_fn=input_fn)
        return text, None, False
    if choice == "5":
        raise SystemExit(0)
    raise ValueError(f"invalid menu choice: {choice!r}")


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="WFM → registry e2e with curated demo pools (G6/G7).")
    p.add_argument(
        "--demo-choice",
        choices=("folio", "pfolio", "stress", "manual"),
        default=None,
        help="Skip menu: pick pool or manual (use with --text/--file for manual).",
    )
    p.add_argument(
        "--demo-seed",
        type=int,
        default=None,
        help="Seed for random curated pick (ignored for manual).",
    )
    p.add_argument("--pool-json", type=Path, default=None, help="Override demo_curated_pools.json path.")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print chosen example / word counts and exit (no Gemini).",
    )
    p.add_argument("--text", type=str, default="", help="Initial rule text (or with --demo-choice manual).")
    p.add_argument("--file", type=Path, default=None, help="UTF-8 file with initial text.")
    p.add_argument("--export", type=Path, default=None, help="Write DevSessionSnapshot JSON after registry.")
    p.add_argument("--handoff", type=Path, default=None, help="Write HandoffBundle JSON before registry.")
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    cfg = load_demo_pool_config(args.pool_json)

    if args.demo_seed is not None and args.demo_choice == "manual":
        print("warning: --demo-seed does not apply to manual input; ignoring.", file=sys.stderr)

    rng = random.Random(args.demo_seed)

    if args.demo_choice is None:
        q1, q2, wpath = _interactive_warm_registry_prompts(input)
        _apply_warm_registry_to_args(args, persist_load=q1, clear_existing=q2, path=wpath)
        limit = compute_manual_word_limit(cfg)
        try:
            initial, ex_id, skip_rule_banner = _interactive_pick(limit=limit, cfg=cfg, rng=rng)
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
            initial, ex_id = _resolve_initial_text(args, rng=rng, cfg=cfg)
        except ManualInputRejected as e:
            print(f"error: {e.word_count} words exceeds manual cap {e.limit}.", file=sys.stderr)
            return 2

    if not skip_rule_banner:
        _print_input_rule_banner(initial, ex_id)

    if args.dry_run:
        wc = word_count(initial)
        print(f"manual_word_limit (G7) = {compute_manual_word_limit(cfg)}")
        if ex_id:
            print(f"example_id: {ex_id}")
        print(f"word_count: {wc}")
        print("(dry-run — no WFM)")
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
        print(f"[Demo] Starting WFM — curated example {ex_id} ({args.demo_choice or 'interactive'}).\n")
    else:
        print("[Demo] Starting WFM — manual input.\n")
    return run_e2e(args, initial)


if __name__ == "__main__":
    raise SystemExit(main())
