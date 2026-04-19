"""
Extract a Z3 unsat core from ``policy_model.smt2`` by tracking each top-level
assertion under its ``; Rule:`` header (v3 comment layout).

Assertions are aligned to rules by parsing the full file once, then mapping
assertion indices using cumulative counts over ``preamble + blocks[0..i]`` (so
sorts and declarations from the preamble remain in scope).

The returned core is a *solver* unsat core over tracked assertions (minimal
among tracked sets in Z3’s sense), not necessarily a globally minimum subset.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

RULE_HEADER = re.compile(
    r"^; Rule: (?P<rid>\S+)\s+\|\s+Line: (?P<li>\d+)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class UnsatCoreReport:
    sat_result: Literal["sat", "unsat", "unknown"]
    unsat_core: Optional[list[str]] = None
    """Tracker ids ``rule_id#assert_index_within_rule``."""
    core_rule_hints: Optional[list[dict[str, Any]]] = None


def _split_preamble_and_rule_blocks(text: str) -> tuple[str, list[tuple[str, int, str]]]:
    text = text.replace("\r\n", "\n")
    matches = list(RULE_HEADER.finditer(text))
    if not matches:
        return text, []

    preamble = text[: matches[0].start()]
    out: list[tuple[str, int, str]] = []
    for i, m in enumerate(matches):
        rid = m.group("rid")
        li = int(m.group("li"))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((rid, li, text[start:end]))
    return preamble, out


def _cumulative_assert_counts(preamble: str, blocks: list[str]) -> list[int]:
    """``cum[i]`` = number of assertions in ``preamble + blocks[0..i-1]``."""
    import z3

    cum: list[int] = [len(z3.parse_smt2_string(preamble))]
    for i in range(len(blocks)):
        chunk = preamble + "".join(blocks[: i + 1])
        cum.append(len(z3.parse_smt2_string(chunk)))
    return cum


def analyze_policy_sat_and_core(policy_text: str) -> UnsatCoreReport:
    import z3

    z3.set_param("unsat-core", True)
    preamble, rule_blocks = _split_preamble_and_rule_blocks(policy_text)
    blocks = [b for _, _, b in rule_blocks]
    rids = [(rid, li) for rid, li, _ in rule_blocks]

    if not blocks:
        # No rule headers: treat whole file as untracked assertions
        solver = z3.Solver()
        for a in z3.parse_smt2_string(policy_text):
            solver.add(a)
        r = solver.check()
        if r == z3.sat:
            return UnsatCoreReport(sat_result="sat")
        if r == z3.unknown:
            return UnsatCoreReport(sat_result="unknown")
        return UnsatCoreReport(sat_result="unsat", unsat_core=[], core_rule_hints=[])

    cum = _cumulative_assert_counts(preamble, blocks)
    asts = z3.parse_smt2_string(policy_text)
    n = len(asts)
    if cum[-1] != n:
        raise ValueError(
            f"assertion count mismatch: cumulative end {cum[-1]} vs full parse {n}"
        )

    solver = z3.Solver()
    for j in range(n):
        rule_i = None
        for i in range(len(blocks)):
            if cum[i] <= j < cum[i + 1]:
                rule_i = i
                break
        if rule_i is None:
            raise RuntimeError(f"assertion index {j} not mapped to any rule")
        rid, _li = rids[rule_i]
        sub = j - cum[rule_i]
        p = z3.Bool(f"{rid}#{sub}")
        solver.assert_and_track(asts[j], p)

    res = solver.check()
    if res == z3.sat:
        return UnsatCoreReport(sat_result="sat")
    if res == z3.unknown:
        return UnsatCoreReport(sat_result="unknown")

    core = solver.unsat_core()
    labels = [str(x) for x in core]

    li_map = {rid: li for rid, li, _ in rule_blocks}
    hints: list[dict[str, Any]] = []
    for lab in labels:
        if "#" in lab:
            rid, _, idx = lab.partition("#")
            h: dict[str, Any] = {
                "rule_id": rid,
                "assert_index": int(idx),
                "track": lab,
                "line_index": li_map.get(rid),
            }
        else:
            h = {"rule_id": None, "assert_index": None, "track": lab}
        hints.append(h)

    return UnsatCoreReport(sat_result="unsat", unsat_core=labels, core_rule_hints=hints)


def analyze_policy_file(path: Path | str) -> UnsatCoreReport:
    p = Path(path)
    return analyze_policy_sat_and_core(p.read_text(encoding="utf-8"))


def report_to_jsonable(r: UnsatCoreReport) -> dict[str, Any]:
    return {
        "sat_result": r.sat_result,
        "unsat_core": r.unsat_core,
        "core_rule_hints": r.core_rule_hints,
    }
