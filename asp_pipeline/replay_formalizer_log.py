"""
Replay ``check_parse_and_ground`` (and optional satisfiability) on ``formalizer_output_lp``
from pipeline ``.log.jsonl`` records (``loop == "parse_ground"``).

Example::

    python -m asp_pipeline.replay_formalizer_log \\
        bundles/asp_from_wfm/symtex_batch_*.log.jsonl --pick last --sat
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from asp_pipeline.clingo_check import check_parse_and_ground, strip_lp_fences
from asp_pipeline.config import AspPipelineConfig
from asp_pipeline.policy_check import run_policy_check


def _load_lp_records(
    log_path: Path,
) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("loop") != "parse_ground":
            continue
        lp = (rec.get("formalizer_output_lp") or "").strip()
        if not lp:
            continue
        it = int(rec.get("iteration") or 0)
        out.append((it, lp))
    return out


def _pick(
    recs: list[tuple[int, str]],
    which: str,
) -> str | None:
    if not recs:
        return None
    if which == "first":
        return recs[0][1]
    return recs[-1][1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Replay parse+ground on formalizer LPs from pipeline .log.jsonl files."
    )
    p.add_argument(
        "logs",
        nargs="+",
        type=Path,
        help="One or more .log.jsonl files (e.g. symtex_batch_*.log.jsonl).",
    )
    p.add_argument(
        "--pick",
        choices=("first", "last"),
        default="last",
        help="Use first or last non-empty formalizer_output_lp per file (default: last).",
    )
    p.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Existing policy .lp to concatenate for grounding (default: empty).",
    )
    p.add_argument(
        "--strip-fences",
        action="store_true",
        help="Run strip_lp_fences() on the LP (usually not needed for stored logs).",
    )
    p.add_argument(
        "--sat",
        action="store_true",
        help="If parse+ground pass, run a one-model policy satisfiability check on the proposed LP only.",
    )
    a = p.parse_args(argv)
    cfg = AspPipelineConfig()
    pol_text = ""
    if a.policy is not None:
        if not a.policy.is_file():
            print(f"policy file not found: {a.policy}", file=sys.stderr)
            return 1
        pol_text = a.policy.read_text(encoding="utf-8")

    all_ok = True
    for log in a.logs:
        if not log.is_file():
            print(f"missing: {log}", file=sys.stderr)
            all_ok = False
            continue
        recs = _load_lp_records(log)
        lp = _pick(recs, a.pick)
        bundle = log.stem
        if lp is None:
            print(f"{log.name}: no non-empty formalizer_output_lp in parse_ground records")
            all_ok = False
            continue
        if a.strip_fences:
            lp = strip_lp_fences(lp)
        ok, stage, err = check_parse_and_ground(
            pol_text,
            lp,
            parse_timeout_sec=cfg.clingo_parse_timeout_sec,
            ground_timeout_sec=cfg.clingo_ground_timeout_sec,
        )
        st = "PASS" if ok else f"FAIL({stage})"
        detail = (err or "").replace("\n", " ")[:200]
        print(f"{st}\t{bundle}\t{log.name}\t{detail}")
        if ok and a.sat:
            fd, name = tempfile.mkstemp(
                prefix=f"replay_{bundle}_",
                suffix=".lp",
                text=True,
            )
            os.close(fd)
            t = Path(name)
            try:
                t.write_text(lp, encoding="utf-8")
                r = run_policy_check(t, max_models=1, timeout_sec=60.0)
                print(f"  sat: {r.get('status')}\t{r.get('detail', '')[:120]}")
            finally:
                t.unlink(missing_ok=True)
        if not ok:
            all_ok = False
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
