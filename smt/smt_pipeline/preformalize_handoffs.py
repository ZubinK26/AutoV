"""
Run the **preformalizer** (v1) over WFM handoff JSON: one Gemini call per line, writing an
enriched handoff with ``preformalized_logic`` filled.

Resume: if ``--output`` already exists, lines with the same ``line_index`` and ``statement_nl``
and non-empty ``preformalized_logic`` are skipped unless ``--force-all``.

Default SMT formalizer remains ``formalizer_v3.md``. After enriching, point the pipeline at the new
handoff and optionally set::

  SMT_PIPELINE_FORMALIZER_PROMPT=formalizer_v3_with_preformalization.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from registry_stage.loaders import load_handoff_bundle
from registry_stage.models import HandoffBundle, HandoffLine, handoff_bundle_to_dict


def _lines_compatible(a: HandoffLine, b: HandoffLine) -> bool:
    return a.line_index == b.line_index and a.statement_nl == b.statement_nl


def _resume_line_map(src: HandoffBundle, existing_path: Path | None) -> dict[int, str]:
    if existing_path is None or not existing_path.is_file():
        return {}
    try:
        exb = load_handoff_bundle(existing_path)
    except (ValueError, OSError, json.JSONDecodeError):
        return {}
    if exb.bundle_id != src.bundle_id:
        return {}
    by_idx = {ln.line_index: ln for ln in exb.lines}
    out: dict[int, str] = {}
    for ln in src.lines:
        hit = by_idx.get(ln.line_index)
        if hit is None:
            continue
        if not _lines_compatible(ln, hit):
            continue
        if hit.preformalized_logic and hit.preformalized_logic.strip():
            out[ln.line_index] = hit.preformalized_logic.strip()
    return out


def preformalize_handoff(
    *,
    source_path: Path,
    output_path: Path,
    dry_run: bool,
    force_all: bool,
    print_fn: Any = print,
) -> int:
    src = load_handoff_bundle(source_path)
    prior: dict[int, str] = {}
    if output_path.is_file() and not force_all:
        prior = _resume_line_map(src, output_path)
        if prior:
            print_fn(f"[resume] reusing {len(prior)} preformalized line(s); fill the rest")

    from smt_pipeline.config import smt_config_from_env
    from smt_pipeline.llm_steps import load_prompt, preformalize_statement_nl

    cfg = smt_config_from_env()
    _ = load_prompt("preformalizer_v1.md")

    new_lines: list[HandoffLine] = []
    for ln in sorted(src.lines, key=lambda x: x.line_index):
        if not force_all and ln.line_index in prior:
            new_lines.append(
                HandoffLine(
                    line_index=ln.line_index,
                    statement_nl=ln.statement_nl,
                    agent3_verdict=ln.agent3_verdict,
                    scope_report=ln.scope_report,
                    diff_report=ln.diff_report,
                    agent2_line_text=ln.agent2_line_text,
                    preformalized_logic=prior[ln.line_index],
                )
            )
            continue
        if dry_run:
            pf = "[dry-run]"
        else:
            try:
                pf = preformalize_statement_nl(ln.statement_nl, cfg=cfg)
            except Exception as e:
                print_fn(f"error at line_index={ln.line_index}: {e}", file=sys.stderr)
                return 1
        new_lines.append(
            HandoffLine(
                line_index=ln.line_index,
                statement_nl=ln.statement_nl,
                agent3_verdict=ln.agent3_verdict,
                scope_report=ln.scope_report,
                diff_report=ln.diff_report,
                agent2_line_text=ln.agent2_line_text,
                preformalized_logic=pf,
            )
        )
        if not dry_run:
            partial = HandoffBundle(
                schema_version=src.schema_version,
                bundle_id=src.bundle_id,
                user_original_input=src.user_original_input,
                lines=new_lines
                + [ln_rest for ln_rest in sorted(src.lines, key=lambda x: x.line_index) if ln_rest.line_index > ln.line_index],
                confirmation_package_style_a=src.confirmation_package_style_a,
                orchestration_run_id=src.orchestration_run_id,
                wfm_pipeline_timestamps=dict(src.wfm_pipeline_timestamps),
                provider_model=src.provider_model,
                wfm_compound_operator_limit=src.wfm_compound_operator_limit,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(handoff_bundle_to_dict(partial), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print_fn(f"[checkpoint] line_index={ln.line_index} → {output_path}")

    out_bundle = HandoffBundle(
        schema_version=src.schema_version,
        bundle_id=src.bundle_id,
        user_original_input=src.user_original_input,
        lines=new_lines,
        confirmation_package_style_a=src.confirmation_package_style_a,
        orchestration_run_id=src.orchestration_run_id,
        wfm_pipeline_timestamps=dict(src.wfm_pipeline_timestamps),
        provider_model=src.provider_model,
        wfm_compound_operator_limit=src.wfm_compound_operator_limit,
    )
    if dry_run:
        print_fn(json.dumps(handoff_bundle_to_dict(out_bundle), indent=2, ensure_ascii=False)[:6000])
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(handoff_bundle_to_dict(out_bundle), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_fn(f"Wrote enriched handoff: {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Preformalize WFM handoff lines (abstract logical sketch per statement_nl)."
    )
    p.add_argument("--handoff", type=Path, default=None, help="Source WFM handoff JSON")
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Enriched handoff JSON (adds preformalized_logic per line)",
    )
    p.add_argument(
        "--handoff-dir",
        type=Path,
        default=None,
        help="Process every *.json in this directory (non-recursive); requires --output-dir",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="With --handoff-dir: write <stem>.preformalized.json here for each input",
    )
    p.add_argument("--dry-run", action="store_true", help="No API; print truncated JSON")
    p.add_argument(
        "--force-all",
        action="store_true",
        help="Re-run the preformalizer for every line (ignore cached preformalized_logic)",
    )
    args = p.parse_args(argv)

    from wfm_orchestration.e2e_context import load_dotenv_for_e2e

    load_dotenv_for_e2e()

    if args.handoff_dir is not None:
        if args.output_dir is None:
            p.error("--handoff-dir requires --output-dir")
        hdir = args.handoff_dir if args.handoff_dir.is_absolute() else _REPO / args.handoff_dir
        odir = args.output_dir if args.output_dir.is_absolute() else _REPO / args.output_dir
        odir.mkdir(parents=True, exist_ok=True)
        files = sorted(hdir.glob("*.json"))
        if not files:
            print("no *.json in handoff-dir", file=sys.stderr)
            return 2
        rc = 0
        for f in files:
            out_f = odir / f"{f.stem}.preformalized.json"
            print(f"--- {f.name} → {out_f.name} ---")
            hp = f
            rc1 = preformalize_handoff(
                source_path=hp,
                output_path=out_f,
                dry_run=args.dry_run,
                force_all=args.force_all,
            )
            if rc1 != 0:
                rc = rc1
        return rc

    if args.handoff is None or args.output is None:
        p.error("either (--handoff and --output) or (--handoff-dir and --output-dir) is required")

    hp = args.handoff if args.handoff.is_absolute() else _REPO / args.handoff
    outp = args.output if args.output.is_absolute() else _REPO / args.output

    return preformalize_handoff(
        source_path=hp,
        output_path=outp,
        dry_run=args.dry_run,
        force_all=args.force_all,
    )


if __name__ == "__main__":
    raise SystemExit(main())
