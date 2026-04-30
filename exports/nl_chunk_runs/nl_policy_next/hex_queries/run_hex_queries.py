"""Run hex_queries/q*.lp against nl_policy_next policy_model.lp; write results_hex_queries.txt

Uses a per-query wall-clock limit (default 90s): full 5x5 Hex search often does not finish.
"""
from __future__ import annotations

import multiprocessing as mp
from pathlib import Path

from clingo import Control

HERE = Path(__file__).resolve().parent
POL = (HERE.parent / "policy_model.lp").read_text(encoding="utf-8")
QUERIES = sorted(HERE.glob("q*.lp"))
OUT = HERE / "results_hex_queries.txt"
TIMEOUT_SEC = 90


def _solve_one(qpath: str, out_q: mp.Queue, opts: list[str]) -> None:
    """Child process: run one clingo solve."""
    try:
        pth = Path(qpath)
        q = pth.read_text(encoding="utf-8")
        c = Control(["-n", "1", "--warn=none", *opts])
        c.add("base", [], POL + "\n\n" + q)
        c.ground([("base", [])])
    except Exception as e:
        out_q.put(("error", str(e)))
        return
    mdl = [None]

    def onm(m):
        mdl[0] = True

    h = c.solve(on_model=onm)
    if h.unsatisfiable:
        out_q.put(("unsat", None))
    elif h.satisfiable and mdl[0]:
        out_q.put(("sat", None))
    else:
        out_q.put(("unknown", str(h)))


def main() -> None:
    lines: list[str] = []
    # Heuristic config helps some existential queries explore faster (not guaranteed).
    opts = ["--configuration=jumpy"]
    for qpath in QUERIES:
        qn = qpath.name
        q = mp.Queue()
        proc = mp.Process(target=_solve_one, args=(str(qpath), q, opts))
        proc.start()
        proc.join(TIMEOUT_SEC)
        if proc.is_alive():
            proc.terminate()
            proc.join(5)
            lines.append(f"=== {qn} ===\nRESULT: TIMEOUT ({TIMEOUT_SEC}s wall clock; search not finished)\n")
            continue
        if not q.empty():
            kind, payload = q.get()
            if kind == "error":
                lines.append(f"=== {qn} ===\nRESULT: ERROR\n{payload}\n\n")
            elif kind == "unsat":
                lines.append(f"=== {qn} ===\nRESULT: UNSAT\n\n")
            elif kind == "sat":
                lines.append(f"=== {qn} ===\nRESULT: SAT (at least one witness answer set)\n\n")
            else:
                lines.append(f"=== {qn} ===\nRESULT: UNKNOWN  {payload}\n\n")
        else:
            lines.append(f"=== {qn} ===\nRESULT: NO_RESULT (child exited without queue)\n\n")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
