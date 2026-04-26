"""
Load **paired** NL + reference ASP from upstream benchmarks for WFM demo / assessment.

Only includes examples where **both** sides come from the same dataset row (no synthetic NL).
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from wfm_orchestration.ground_truth_asp import (
    truth_assessment_asp_nl_bench,
    truth_assessment_symtex_paired,
)

SCHEMA_ASSESSMENT = "wfm_asp_demo_assessment_v1"

SymTexTask = Literal["answerset_generation", "answerset_selection", "fact_state_querying"]


@dataclass(frozen=True)
class SymTexPairedExample:
    """One SymTex row: English (textual JSONL) + ASP reference (symbolic JSONL), same ``id``."""

    task: SymTexTask
    source_id: str
    nl_document: str
    reference_asp_program: str
    textual_jsonl_relpath: str
    symbolic_jsonl_relpath: str
    extra: dict[str, Any]

    @property
    def manifest_example_id(self) -> str:
        return f"ASPBench-{self.task}-{self.source_id}"[:240]


def _repo_symtex_dir(repo_root: Path) -> Path:
    return repo_root / "test_sets" / "datasets" / "aspbench" / "repo" / "datasets" / "SymTex"


def symtex_clone_present(repo_root: Path) -> bool:
    d = _repo_symtex_dir(repo_root)
    return d.is_dir() and any(d.glob("*.jsonl"))


def _format_nl_facts_rules(*, facts: list[str], rules: list[str]) -> str:
    """Verbatim strings from the dataset; only section labels added."""
    flines = "\n".join(facts)
    rlines = "\n".join(rules)
    return (
        "The following facts and rules are quoted verbatim from the benchmark instance.\n\n"
        "Facts:\n"
        f"{flines}\n\n"
        "Rules:\n"
        f"{rlines}"
    )


def _reference_from_gen_sel(sym_row: dict[str, Any]) -> str:
    facts = sym_row.get("facts") or []
    rules = sym_row.get("rules") or []
    return "\n".join(facts) + ("\n" + "\n".join(rules) if rules else "")


def _load_id_map(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        oid = obj.get("id")
        if isinstance(oid, str):
            out[oid] = obj
    return out


def _pair_gen_or_sel(
    *,
    task: SymTexTask,
    repo_root: Path,
    symtex_dir: Path,
    textual_name: str,
    symbolic_name: str,
) -> list[SymTexPairedExample]:
    textual_path = symtex_dir / textual_name
    symbolic_path = symtex_dir / symbolic_name
    if not textual_path.is_file() or not symbolic_path.is_file():
        return []
    sym_map = _load_id_map(symbolic_path)
    rel_t = str(textual_path.relative_to(repo_root))
    rel_s = str(symbolic_path.relative_to(repo_root))
    out: list[SymTexPairedExample] = []
    for line in textual_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        oid = row.get("id")
        if not isinstance(oid, str) or oid not in sym_map:
            continue
        facts = row.get("facts") or []
        rules = row.get("rules") or []
        if not facts and not rules:
            continue
        nl = _format_nl_facts_rules(facts=facts, rules=rules)
        ref = _reference_from_gen_sel(sym_map[oid])
        if not ref.strip():
            continue
        extra: dict[str, Any] = {
            "num_answer_sets": row.get("num_answer_sets"),
            "source_type": row.get("source_type"),
        }
        out.append(
            SymTexPairedExample(
                task=task,
                source_id=oid,
                nl_document=nl,
                reference_asp_program=ref,
                textual_jsonl_relpath=rel_t,
                symbolic_jsonl_relpath=rel_s,
                extra=extra,
            )
        )
    return out


def _pair_fact_state(
    *,
    repo_root: Path,
    symtex_dir: Path,
) -> list[SymTexPairedExample]:
    textual_path = symtex_dir / "fact_state_querying_textual.jsonl"
    symbolic_path = symtex_dir / "fact_state_querying_symbolic.jsonl"
    if not textual_path.is_file() or not symbolic_path.is_file():
        return []
    sym_map = _load_id_map(symbolic_path)
    rel_t = str(textual_path.relative_to(repo_root))
    rel_s = str(symbolic_path.relative_to(repo_root))
    out: list[SymTexPairedExample] = []
    for line in textual_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        oid = row.get("id")
        if not isinstance(oid, str) or oid not in sym_map:
            continue
        tprog = (row.get("asp_program_dlv2") or {}) if isinstance(row.get("asp_program_dlv2"), dict) else {}
        tfacts = tprog.get("noiseless_facts") or []
        trules = tprog.get("noiseless_rules") or []
        if not tfacts and not trules:
            continue
        nl = _format_nl_facts_rules(facts=tfacts, rules=trules)
        srow = sym_map[oid]
        sprog = (srow.get("asp_program_dlv2") or {}) if isinstance(srow.get("asp_program_dlv2"), dict) else {}
        sfacts = sprog.get("noiseless_facts") or []
        srules = sprog.get("noiseless_rules") or []
        ref = "\n".join(sfacts) + ("\n" + "\n".join(srules) if srules else "")
        if not ref.strip():
            continue
        extra = {
            "target_query": row.get("target_query"),
            "target_query_in_answerset": row.get("target_query_in_answerset"),
            "label": row.get("label"),
            "source_type": row.get("source_type"),
        }
        out.append(
            SymTexPairedExample(
                task="fact_state_querying",
                source_id=oid,
                nl_document=nl,
                reference_asp_program=ref,
                textual_jsonl_relpath=rel_t,
                symbolic_jsonl_relpath=rel_s,
                extra=extra,
            )
        )
    return out


def load_symtex_paired_index(repo_root: Path) -> list[SymTexPairedExample]:
    """
    All SymTex instances that have matching textual + symbolic rows.

    Raises FileNotFoundError if the ASPBench clone is missing.
    """
    symtex_dir = _repo_symtex_dir(repo_root)
    if not symtex_dir.is_dir():
        raise FileNotFoundError(
            f"ASPBench SymTex directory not found: {symtex_dir}\n"
            "Clone: git clone https://github.com/HomuraT/ASPBench.git "
            "test_sets/datasets/aspbench/repo"
        )
    acc: list[SymTexPairedExample] = []
    acc.extend(
        _pair_gen_or_sel(
            task="answerset_generation",
            repo_root=repo_root,
            symtex_dir=symtex_dir,
            textual_name="answerset_generation_textual.jsonl",
            symbolic_name="answerset_generation_symbolic.jsonl",
        )
    )
    acc.extend(
        _pair_gen_or_sel(
            task="answerset_selection",
            repo_root=repo_root,
            symtex_dir=symtex_dir,
            textual_name="answerset_selection_textual.jsonl",
            symbolic_name="answerset_selection_symbolic.jsonl",
        )
    )
    acc.extend(_pair_fact_state(repo_root=repo_root, symtex_dir=symtex_dir))
    if not acc:
        raise RuntimeError(f"No paired SymTex rows under {symtex_dir} (empty or mismatched files).")
    return acc


def compute_asp_manual_word_limit(paired: list[SymTexPairedExample], *, extra: int = 40) -> int:
    max_w = 0
    for ex in paired:
        max_w = max(max_w, len(ex.nl_document.split()))
    return max_w + extra


def pick_symtex_example(
    paired: list[SymTexPairedExample],
    *,
    rng: random.Random,
    exclude_ids: set[str] | None = None,
) -> SymTexPairedExample:
    excl = exclude_ids or set()
    pool = [x for x in paired if x.manifest_example_id not in excl]
    if not pool:
        raise ValueError("no SymTex examples left (all excluded)")
    return rng.choice(pool)


# --- NL ASP-Bench (arXiv:2602.01171): only if user vendored `installed.json` ---

ASP_NL_INSTALLED = Path("test_sets/datasets/asp_nl_bench/installed.json")


@dataclass(frozen=True)
class AspNlBenchExample:
    source_id: str
    nl_document: str
    reference_asp_program: str
    provenance: str


def asp_nl_bench_status(repo_root: Path) -> tuple[bool, str]:
    """
    Returns (available, message). We do **not** synthesize problems; user must add ``installed.json``.
    """
    path = repo_root / ASP_NL_INSTALLED
    if not path.is_file():
        return (
            False,
            "NL ASP-Bench (Szeider et al., arXiv:2602.01171) is not configured. "
            "Official problems are on Zenodo https://doi.org/10.5281/zenodo.18062939 (see paper for the archive). "
            "That benchmark is separate from github.com/HomuraT/ASPBench (use demo option 1 for SymTex). "
            f"After you build a JSONL, add `{ASP_NL_INSTALLED.as_posix()}` — see `installed.example.json`.",
        )
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"Invalid installed.json: {e}"
    pj = cfg.get("problems_jsonl")
    if not isinstance(pj, str) or not pj.strip():
        return False, "installed.json must set non-empty `problems_jsonl` path."
    p = Path(pj)
    if not p.is_absolute():
        p = (path.parent / p).resolve()
    if not p.is_file():
        return False, f"problems_jsonl not found: {p}"
    return True, str(p)


def load_asp_nl_bench_index(repo_root: Path) -> list[AspNlBenchExample]:
    ok, msg = asp_nl_bench_status(repo_root)
    if not ok:
        raise FileNotFoundError(msg)
    path = Path(msg)
    out: list[AspNlBenchExample] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        oid = row.get("id")
        nl = row.get("nl") or row.get("natural_language")
        asp = row.get("reference_asp") or row.get("reference_lp") or row.get("program")
        if not isinstance(oid, str) or not isinstance(nl, str) or not isinstance(asp, str):
            continue
        if not nl.strip() or not asp.strip():
            continue
        prov = row.get("provenance")
        out.append(
            AspNlBenchExample(
                source_id=oid,
                nl_document=nl.strip(),
                reference_asp_program=asp.strip(),
                provenance=str(prov) if prov is not None else str(path),
            )
        )
    if not out:
        raise RuntimeError(f"No valid rows in {path} (need id, nl, reference_asp per line).")
    return out


def pick_asp_nl_example(
    rows: list[AspNlBenchExample],
    *,
    rng: random.Random,
    exclude_ids: set[str] | None = None,
) -> AspNlBenchExample:
    excl = exclude_ids or set()
    pool = [x for x in rows if x.source_id not in excl]
    if not pool:
        raise ValueError("no NL ASP-Bench examples left (all excluded)")
    return rng.choice(pool)


def write_wfm_asp_assessment(
    *,
    repo_root: Path,
    bundle_id: str,
    handoff_path: Path | None,
    dataset_record: dict[str, Any],
    dev_session_notes: str | None,
) -> Path:
    """Write JSON for offline comparison of WFM output to dataset reference programs."""
    out_dir = repo_root / "exports" / "wfm_asp_demo_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    safe_bid = bundle_id.replace("/", "_")[:120]
    out_path = out_dir / f"{stamp}_{safe_bid}_assessment.json"
    truth = dataset_record.get("truth_assessment")
    if not isinstance(truth, dict):
        truth = None
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_ASSESSMENT,
        "utc_timestamp": stamp,
        "bundle_id": bundle_id,
        "handoff_path": str(handoff_path.resolve()) if handoff_path is not None else None,
        "dev_session_notes": dev_session_notes,
        "dataset": dataset_record,
    }
    if truth is not None:
        payload["truth_assessment"] = truth
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def symtex_record_to_assessment_dict(ex: SymTexPairedExample) -> dict[str, Any]:
    d = asdict(ex)
    d["upstream"] = "HomuraT/ASPBench SymTex (textual + symbolic JSONL, same id)"
    d["paper"] = "https://arxiv.org/abs/2507.19749"
    d["truth_assessment"] = truth_assessment_symtex_paired(ex)
    return d


def asp_nl_record_to_assessment_dict(ex: AspNlBenchExample) -> dict[str, Any]:
    d: dict[str, Any] = {
        "dataset": "asp_nl_bench",
        "source_id": ex.source_id,
        "nl_document": ex.nl_document,
        "reference_asp_program": ex.reference_asp_program,
        "provenance": ex.provenance,
        "upstream": "ASP-Bench: From Natural Language to Logic Programs (arXiv:2602.01171)",
        "paper": "https://arxiv.org/abs/2602.01171",
    }
    d["truth_assessment"] = truth_assessment_asp_nl_bench()
    return d
