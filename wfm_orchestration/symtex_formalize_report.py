"""
After SymTex WFM + asp_pipeline, compare committed ``.lp`` to benchmark reference ASP, SAT, and
first-model atom overlap (heuristic; encoding/casing can differ).

From repo root::

  python -m wfm_orchestration.symtex_formalize_report --bundle-prefix symtex_batch_20260423_
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_REPO))

_DEFAULT_POLICY = _REPO / "bundles" / "asp_from_wfm" / "policies"
_DEFAULT_BUNDLES = _REPO / "bundles" / "asp_from_wfm"
_DEFAULT_OUT = _REPO / "exports" / "symtex_formalize_reports"


def _norm_atom(s: str) -> str:
    t = s.strip().lower()
    return re.sub(r"\s+", "", t)


def _first_shown_model_atoms(lp: str) -> tuple[str, set[str]]:
    try:
        from clingo import Control
    except ImportError as e:
        return (f"no_clingo: {e}", set())
    shown: list[str] = []

    def on_model(m) -> bool:
        for x in m.symbols(shown=True):
            shown.append(str(x))
        return False

    try:
        c = Control()
        c.add("base", [], lp)
        c.ground([("base", [])])
        c.solve(on_model=on_model)
    except Exception as e:  # noqa: BLE001
        return (f"clingo_error: {e!s}"[:2000], set())
    if not shown:
        return ("no_shown_atoms", set())
    return ("ok", {_norm_atom(x) for x in shown})


def _find_paired(example_key: str, index: list[Any]) -> Any | None:
    if ":" not in example_key:
        return None
    task, source_id = example_key.split(":", 1)
    for ex in index:
        if ex.task == task and ex.source_id == source_id:
            return ex
    return None


@dataclass
class OneRow:
    example_key: str
    bundle_id: str
    policy_lp_path: str | None
    bundle_asp_path: str | None
    committed: bool
    policy_sat: str | None
    ref_sat: str | None
    first_model_jaccard: float | None
    first_model_note: str
    wfm_in_scope_lines: int
    wfm_out_of_scope_lines: int
    policy_rule_ids_count: int | None
    nl_chars: int
    policy_lp_bytes: int | None
    ref_lp_bytes: int
    analysis: str


def _load_completed_rows(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def build_report(
    *,
    completed_path: Path,
    repo_root: Path,
    only_bundle_id_prefix: str | None = None,
) -> list[OneRow]:
    from wfm_orchestration.asp_demo_sources import load_symtex_paired_index
    from asp_pipeline.policy_check import run_policy_check

    index = load_symtex_paired_index(repo_root)
    completed = _load_completed_rows(completed_path)
    tmpdir = _DEFAULT_OUT / ".tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    rows: list[OneRow] = []

    for rec in completed:
        if not rec.get("success"):
            continue
        ek = rec.get("example_key")
        bid = rec.get("bundle_id")
        if not isinstance(ek, str) or not isinstance(bid, str):
            continue
        if only_bundle_id_prefix and not bid.startswith(only_bundle_id_prefix):
            continue
        ex = _find_paired(ek, index)
        if ex is None:
            rows.append(
                OneRow(
                    example_key=ek,
                    bundle_id=bid,
                    policy_lp_path=None,
                    bundle_asp_path=None,
                    committed=False,
                    policy_sat=None,
                    ref_sat=None,
                    first_model_jaccard=None,
                    first_model_note="index_miss",
                    wfm_in_scope_lines=0,
                    wfm_out_of_scope_lines=0,
                    policy_rule_ids_count=None,
                    nl_chars=0,
                    policy_lp_bytes=None,
                    ref_lp_bytes=0,
                    analysis="No SymTex pair for this example_key.",
                )
            )
            continue

        pol = _DEFAULT_POLICY / f"{bid}.lp"
        bjson = _DEFAULT_BUNDLES / f"{bid}.json"
        ref_lp = (ex.reference_asp_program or "").strip()
        try:
            d = json.loads(bjson.read_text(encoding="utf-8")) if bjson.is_file() else {}
        except (json.JSONDecodeError, OSError):
            d = {}
        committed = (
            bjson.is_file()
            and d.get("pipeline_status") == "committed"
            and d.get("pipeline_kind") == "asp_clincon"
        )
        prules = d.get("rule_ids") or []
        n_rules = len(prules) if isinstance(prules, list) else None
        handoff_p = rec.get("handoff_path")
        n_in = 0
        n_ex = 0
        if isinstance(handoff_p, str) and Path(handoff_p).is_file():
            hd = json.loads(Path(handoff_p).read_text(encoding="utf-8"))
            for ln in hd.get("lines") or []:
                if (ln or {}).get("agent3_verdict", "").strip().upper() != "OUT_OF_SCOPE":
                    n_in += 1
                else:
                    n_ex += 1
        nl_len = len((ex.nl_document or ""))
        p_lp_text = pol.read_text(encoding="utf-8") if pol.is_file() else ""

        ref_path = tmpdir / f"ref_{bid}.lp"
        ref_path.write_text(ref_lp, encoding="utf-8")
        p_chk = run_policy_check(pol, max_models=1, timeout_sec=120.0) if pol.is_file() else {"status": "NO_FILE"}
        r_chk = run_policy_check(ref_path, max_models=1, timeout_sec=120.0)
        p_sat = str(p_chk.get("status"))
        ref_sat = str(r_chk.get("status"))

        err1, s_ref = _first_shown_model_atoms(ref_lp)
        err2, s_pol = _first_shown_model_atoms(p_lp_text) if p_lp_text.strip() else ("empty_policy", set())
        if err1 != "ok":
            jnote, jacc = f"reference: {err1}", None
        elif err2 != "ok":
            jnote, jacc = f"policy: {err2}", None
        else:
            u = len(s_ref | s_pol) or 1
            jacc = len(s_ref & s_pol) / u
            jnote = "Jaccard on first model shown atoms (normalized strings; not logical equivalence)."

        analysis = (
            f"WFM input is the SymTex-formatted NL text; the formalizer turns in-scope WFM lines into "
            f"ASP (here {n_rules or '?'} rule_ids in bundle). Reference LP is {len(ref_lp)} chars; "
            f"policy LP is {len(p_lp_text)} chars. SAT: ref={ref_sat} policy={p_sat}. "
            f"First-model atom overlap (heuristic): {jacc if jacc is not None else 'n/a'} — {jnote}"
        )

        rows.append(
            OneRow(
                example_key=ek,
                bundle_id=bid,
                policy_lp_path=str(pol) if pol.is_file() else None,
                bundle_asp_path=str(bjson) if bjson.is_file() else None,
                committed=committed,
                policy_sat=p_sat,
                ref_sat=ref_sat,
                first_model_jaccard=jacc,
                first_model_note=jnote,
                wfm_in_scope_lines=n_in,
                wfm_out_of_scope_lines=n_ex,
                policy_rule_ids_count=n_rules,
                nl_chars=nl_len,
                policy_lp_bytes=len(p_lp_text.encode("utf-8")) if p_lp_text else None,
                ref_lp_bytes=len(ref_lp.encode("utf-8")),
                analysis=analysis,
            )
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Report SAT + first-model vs reference for SymTex formalized runs.")
    p.add_argument(
        "--from-completed",
        type=Path,
        default=_REPO / "exports" / "wfm_symtex_batch" / "completed.jsonl",
    )
    p.add_argument(
        "--bundle-prefix",
        type=str,
        default=None,
        help="e.g. symtex_batch_20260423_ to only include one batch date run.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
    )
    args = p.parse_args(argv)
    out_path = args.out
    if out_path is None:
        _DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
        st = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        out_path = _DEFAULT_OUT / f"{st}_formalize_report.json"

    rows = build_report(
        completed_path=args.from_completed,
        repo_root=_REPO,
        only_bundle_id_prefix=args.bundle_prefix,
    )
    payload: dict[str, Any] = {
        "schema": "symtex_formalize_report_v1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "rows": [asdict(x) for x in rows],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out_path.resolve()), "n": len(rows)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
