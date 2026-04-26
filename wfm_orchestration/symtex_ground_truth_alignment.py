"""
Compare committed formalizer ``.lp`` to SymTex **reference_asp** on a **heuristic, witness basis**:

* Normalize reference LP (DLV ``"- pred"`` → ``-pred``, string constants → unquoted lower-case symbols) for Clingo.
* Take the **first** Clingo model’s **#shown** atoms, drop ``person(…)`` (formalizer helper), normalize strings, Jaccard overlap.
* For ``fact_state_querying`` rows, if ``target_query`` is in :class:`extra`, check whether a matching atom appears in
  the first model of **both** programs (benchmark’s intended “task” literal).

**This does not prove** strong equivalence of two ASP programs. It **does** answer “if I swapped in our policy, would
the first standard witness model look *compatible* with the ground-truth’s first model on the same vocabulary
(normalized)?” and whether the **official target** literal is shared when provided.

From repo root::

  python -m wfm_orchestration.symtex_ground_truth_alignment --bundle-prefix symtex_batch_20260423_ \\
      --out exports/symtex_formalize_reports/align_8.json
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

_DEFAULT_POLICIES = _REPO / "bundles" / "asp_from_wfm" / "policies"
_DEFAULT_COMPLETED = _REPO / "exports" / "wfm_symtex_batch" / "completed.jsonl"
_DEFAULT_OUT = _REPO / "exports" / "symtex_formalize_reports"


def _ref_lp_for_clingo_gentle(raw: str) -> str:
    """DLV space after '-', and quoted names → clingo function symbols (lowercased unquoted)."""
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("%"):
            lines.append(s)
            continue
        m = re.match(r"^-\s+(.+)$", s)
        if m:
            s = "-" + m.group(1).lstrip()
        s = re.sub(
            r'"([^"]+)"',
            lambda m2: m2.group(1).lower().replace(" ", "_").replace(".", "_"),
            s,
        )
        lines.append(s)
    return "\n".join(lines)


def _norm_atom(s: str) -> str:
    t = s.strip().lower()
    t = re.sub(r"\s+", "", t)
    return t


def _is_person_atom(n: str) -> bool:
    t = n.strip().lower()
    return t.startswith("person(") and t.count("(") == 1


def _first_model_shown(text: str) -> tuple[str, set[str] | None, str | None]:
    try:
        from clingo import Control
    except ImportError as e:
        return ("no_clingo", None, str(e))
    acc: set[str] = set()
    first = True

    def on_model(m) -> bool:
        nonlocal first, acc
        if not first:
            return True
        for s in m.symbols(shown=True):
            t = str(s)
            a = _norm_atom(t)
            if _is_person_atom(a):
                continue
            acc.add(a)
        first = False
        return True

    try:
        c = Control()
        c.add("base", [], text)
        c.ground([("base", [])])
        c.solve(on_model=on_model)
    except Exception as e:  # noqa: BLE001
        return ("parse_ground", None, str(e)[:4000])
    return ("ok", acc, None)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    if u == 0:
        return 1.0
    return len(a & b) / u


def _target_to_norm_atom(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    t = s.strip().rstrip(".")
    t = re.sub(
        r'"([^"]+)"',
        lambda m2: m2.group(1).lower().replace(" ", "_").replace(".", "_"),
        t,
    )
    t = t.replace(" ", "")
    return _norm_atom(t) if t else None


@dataclass
class Row:
    example_key: str
    bundle_id: str
    task: str
    ref_parse_status: str
    pol_parse_status: str
    jaccard_first_shown: float | None
    ref_only_count: int | None
    pol_only_count: int | None
    target_query_raw: str | None
    target_in_ref_first: bool | None
    target_in_policy_first: bool | None
    substitute_risk: str
    notes: str


def _load_completed(p: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _find_ex(example_key: str, index: list[Any]) -> Any | None:
    if ":" not in example_key:
        return None
    t, sid = example_key.split(":", 1)
    for e in index:
        if e.task == t and e.source_id == sid:
            return e
    return None


def _substitute_risk(
    j: float | None,
    t_ref: bool | None,
    t_pol: bool | None,
    task: str,
) -> str:
    """
    Plain-language: would swapping in policy for benchmark ref **likely** make incompatible claims vs GT witness?
    Heuristic only.
    """
    if t_ref is not None and t_pol is not None and task == "fact_state_querying":
        if t_ref and t_pol:
            return "low_for_target_literal_both_witnesses_include_it"
        if t_ref and not t_pol:
            return "high_target_true_in_ref_first_but_missing_in_policy_first"
        if (not t_ref) and t_pol:
            return "high_target_in_policy_not_in_ref_first"
        return "low_target_absent_both"
    if j is None:
        return "inconclusive_cannot_compare_models"
    if j >= 0.65:
        return "low_divergence_first_witness_significant_overlap"
    if j >= 0.25:
        return "medium_divergence_some_overlap"
    return "high_divergence_few_shown_atoms_in_common_different_rewriting"


def build(
    *,
    completed_path: Path,
    policy_dir: Path,
    bundle_prefix: str,
    repo_root: Path,
) -> list[Row]:
    from wfm_orchestration.asp_demo_sources import load_symtex_paired_index

    index = load_symtex_paired_index(repo_root)
    done = _load_completed(completed_path)
    out: list[Row] = []
    for rec in done:
        if not rec.get("success") or not isinstance(rec.get("bundle_id"), str):
            continue
        bid = rec["bundle_id"]
        if not bid.startswith(bundle_prefix):
            continue
        ek = rec.get("example_key")
        if not isinstance(ek, str):
            continue
        ex = _find_ex(ek, index)
        pol_path = policy_dir / f"{bid}.lp"
        if ex is None or not pol_path.is_file():
            out.append(
                Row(
                    example_key=ek,
                    bundle_id=bid,
                    task=ek.split(":", 1)[0] if ":" in ek else "",
                    ref_parse_status="no_index" if ex is None else "no_policy",
                    pol_parse_status="ok" if pol_path.is_file() else "no_file",
                    jaccard_first_shown=None,
                    ref_only_count=None,
                    pol_only_count=None,
                    target_query_raw=None,
                    target_in_ref_first=None,
                    target_in_policy_first=None,
                    substitute_risk="inconclusive_missing_artifact",
                    notes="",
                )
            )
            continue

        ref_raw = ex.reference_asp_program
        ref_lp = _ref_lp_for_clingo_gentle(ref_raw)
        pol_lp = pol_path.read_text(encoding="utf-8")
        tq_raw = (ex.extra or {}).get("target_query")
        tq = tq_raw.strip() if isinstance(tq_raw, str) and tq_raw.strip() else None
        n_tq = _target_to_norm_atom(tq) if tq else None

        st_r, a_r, err_r = _first_model_shown(ref_lp)
        st_p, a_p, err_p = _first_model_shown(pol_lp)
        if a_r is None or a_p is None:
            j = None
            oc = oi = None
        else:
            j = _jaccard(a_r, a_p)
            oc = len(a_r - a_p)
            oi = len(a_p - a_r)

        in_ref = in_pol = None
        if n_tq is not None and a_r is not None and a_p is not None:
            in_ref = n_tq in a_r
            in_pol = n_tq in a_p

        task = ex.task
        row = Row(
            example_key=ek,
            bundle_id=bid,
            task=task,
            ref_parse_status=st_r,
            pol_parse_status=st_p,
            jaccard_first_shown=round(j, 6) if j is not None else None,
            ref_only_count=oc,
            pol_only_count=oi,
            target_query_raw=tq_raw if isinstance(tq_raw, str) else tq,
            target_in_ref_first=in_ref,
            target_in_policy_first=in_pol,
            substitute_risk=_substitute_risk(j, in_ref, in_pol, task),
            notes="; ".join(
                x
                for x in [
                    f"ref={err_r}" if err_r else None,
                    f"pol={err_p}" if err_p else None,
                ]
                if x
            ),
        )
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-completed", type=Path, default=_DEFAULT_COMPLETED)
    ap.add_argument("--policy-dir", type=Path, default=_DEFAULT_POLICIES)
    ap.add_argument("--bundle-prefix", type=str, required=True)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    out = a.out
    if out is None:
        _DEFAULT_OUT.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        out = _DEFAULT_OUT / f"{ts}_ground_truth_alignment.json"
    rows = build(
        completed_path=a.from_completed,
        policy_dir=a.policy_dir,
        bundle_prefix=a.bundle_prefix,
        repo_root=_REPO,
    )
    payload: dict[str, Any] = {
        "schema": "symtex_ground_truth_alignment_v1",
        "disclaimer": (
            "Heuristic: first Clingo #shown model, person/1 removed, DLV ref normalized. "
            "Not a proof of logical equivalence. Use for policy swap risk triage, not formal verification."
        ),
        "utc": datetime.now(timezone.utc).isoformat(),
        "rows": [asdict(x) for x in rows],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out), "n": len(rows)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
