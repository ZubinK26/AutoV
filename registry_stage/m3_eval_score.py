"""
Grade a Lane A JSONL file against ``eval_fixtures/m3_eval_labels.json`` (no API).

Usage::

    python -m registry_stage.m3_eval_score \\
        --jsonl registry_stage/eval_runs/eval_try.jsonl \\
        --labels registry_stage/eval_fixtures/m3_eval_labels.json

Exit code 0 if all groups pass every labeled line. Groups are keyed by
``(query_mode, masking_preset, authoritative_min_score)`` so min-score sweeps
(distinct JSONL runs or mixed rows) stay separated.

exit 1 on any failure unless ``--warn`` (print only, exit 0).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _norm_min_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


@dataclass
class LineLabel:
    example_id: str
    required_authoritative_entry_ids: tuple[str, ...]
    expected_gap_substrings: tuple[str, ...]
    notes: str = ""


@dataclass
class CheckResult:
    example_id: str
    retrieval_ok: bool
    gaps_ok: bool
    retrieval_missing: tuple[str, ...] = ()
    gaps_missing: tuple[str, ...] = ()
    gap_fields_used: str = ""


@dataclass
class GroupReport:
    query_mode: str
    masking_preset: str
    authoritative_min_score: float | None
    semantic_backend_label: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(r.retrieval_ok and r.gaps_ok for r in self.results)


def load_labels(path: Path) -> tuple[bool, bool, list[LineLabel]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    chk_auth = bool(data.get("check_authoritative", True))
    chk_gaps = bool(data.get("check_gaps", True))
    raw_lines = data.get("lines")
    if not isinstance(raw_lines, list):
        raise ValueError("labels file needs 'lines' array")
    labels: list[LineLabel] = []
    for i, row in enumerate(raw_lines):
        if not isinstance(row, dict):
            continue
        eid = row.get("id")
        if not isinstance(eid, str) or not eid:
            raise ValueError(f"labels.lines[{i}] needs string 'id'")
        req = row.get("required_authoritative_entry_ids") or []
        if not isinstance(req, list):
            raise ValueError(f"labels.lines[{i}].required_authoritative_entry_ids must be a list")
        exp = row.get("expected_gap_substrings") or []
        if not isinstance(exp, list):
            raise ValueError(f"labels.lines[{i}].expected_gap_substrings must be a list")
        notes = row.get("notes") or ""
        labels.append(
            LineLabel(
                example_id=eid,
                required_authoritative_entry_ids=tuple(str(x) for x in req),
                expected_gap_substrings=tuple(str(x) for x in exp),
                notes=str(notes),
            )
        )
    return chk_auth, chk_gaps, labels


def _authoritative_ids(row: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for h in row.get("authoritative_hits") or []:
        if isinstance(h, dict) and isinstance(h.get("entry_id"), str):
            out.add(h["entry_id"])
    return out


def _gap_blob(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for s in row.get("gap_spans") or []:
        if isinstance(s, str):
            parts.append(s)
    for g in row.get("structured_gaps") or []:
        if isinstance(g, dict) and isinstance(g.get("surface"), str):
            parts.append(g["surface"])
    return " | ".join(parts).lower()


def check_row(
    row: dict[str, Any],
    label: LineLabel,
    *,
    check_authoritative: bool,
    check_gaps: bool,
) -> CheckResult:
    auth = _authoritative_ids(row)
    missing_ret: list[str] = []
    if check_authoritative:
        for eid in label.required_authoritative_entry_ids:
            if eid not in auth:
                missing_ret.append(eid)
    retrieval_ok = not missing_ret

    blob = _gap_blob(row)
    missing_gaps: list[str] = []
    if check_gaps:
        for sub in label.expected_gap_substrings:
            if sub.lower() not in blob:
                missing_gaps.append(sub)
    gaps_ok = not missing_gaps

    return CheckResult(
        example_id=label.example_id,
        retrieval_ok=retrieval_ok,
        retrieval_missing=tuple(missing_ret),
        gaps_ok=gaps_ok,
        gaps_missing=tuple(missing_gaps),
        gap_fields_used=blob[:200] + ("…" if len(blob) > 200 else ""),
    )


def parse_jsonl_results(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    header: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if obj.get("row_kind") == "header":
                header = obj
            elif obj.get("row_kind") == "result":
                results.append(obj)
    return header, results


def score_jsonl(
    jsonl_path: Path,
    labels_path: Path,
) -> tuple[dict[str, Any], dict[tuple[str, str, float | None], GroupReport]]:
    check_auth, check_gaps, labels = load_labels(labels_path)
    label_by_id = {lb.example_id: lb for lb in labels}
    header, rows = parse_jsonl_results(jsonl_path)

    groups: dict[tuple[str, str, float | None], GroupReport] = {}
    for row in rows:
        eid = row.get("example_id")
        qm = row.get("query_mode")
        mp = row.get("masking_preset")
        if not isinstance(eid, str) or not isinstance(qm, str) or not isinstance(mp, str):
            continue
        if eid not in label_by_id:
            continue
        ms = _norm_min_score(row.get("authoritative_min_score"))
        key = (qm, mp, ms)
        if key not in groups:
            groups[key] = GroupReport(
                query_mode=qm,
                masking_preset=mp,
                authoritative_min_score=ms,
                semantic_backend_label=str(row.get("semantic_backend_label", "")),
            )
        cr = check_row(row, label_by_id[eid], check_authoritative=check_auth, check_gaps=check_gaps)
        groups[key].results.append(cr)

    return header, groups


def _group_report_sort_key(k: tuple[str, str, float | None]) -> tuple[str, str, float]:
    qm, mp, ms = k
    return (qm, mp, float("-inf") if ms is None else ms)


def print_report(header: dict[str, Any], groups: dict[tuple[str, str, float | None], GroupReport]) -> None:
    print("=== Lane A JSONL score (labeled expectations) ===\n")
    if header:
        print(f"jsonl timestamp: {header.get('timestamp_utc', '')}")
        print(f"registry: {header.get('registry_path', '')}")
        print(f"index_mode: {header.get('index_mode', '')}")
        print(f"prompt_sha256: {list((header.get('prompt_sha256') or {}).keys())}")
        print()

    for (qm, mp, _ms), rep in sorted(groups.items(), key=lambda kv: _group_report_sort_key(kv[0])):
        ok = rep.all_ok
        n = len(rep.results)
        pass_n = sum(1 for r in rep.results if r.retrieval_ok and r.gaps_ok)
        score_part = (
            f" / authoritative_min_score={rep.authoritative_min_score}"
            if rep.authoritative_min_score is not None
            else ""
        )
        print(f"## {qm} / {mp}{score_part}  ({pass_n}/{n} lines pass)  {'OK' if ok else 'FAIL'}")
        print(f"   backend={rep.semantic_backend_label}")
        for r in sorted(rep.results, key=lambda x: x.example_id):
            status = "OK" if (r.retrieval_ok and r.gaps_ok) else "FAIL"
            print(f"   - [{status}] {r.example_id}")
            if not r.retrieval_ok:
                print(f"       retrieval missing: {list(r.retrieval_missing)}")
            if not r.gaps_ok:
                print(f"       gaps missing (substring not in gap_spans/structured surfaces): {list(r.gaps_missing)}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Score Lane A JSONL against m3_eval_labels.json (no API).")
    parser.add_argument("--jsonl", type=Path, required=True)
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path(__file__).resolve().parent / "eval_fixtures" / "m3_eval_labels.json",
    )
    parser.add_argument(
        "--warn",
        action="store_true",
        help="print report but always exit 0 (default: exit 1 if any check fails)",
    )
    args = parser.parse_args()
    header, groups = score_jsonl(args.jsonl, args.labels)
    print_report(header, groups)
    any_fail = any(not rep.all_ok for rep in groups.values())
    if any_fail and not args.warn:
        sys.exit(1)


if __name__ == "__main__":
    main()
