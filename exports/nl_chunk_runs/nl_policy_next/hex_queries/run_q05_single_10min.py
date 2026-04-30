"""
Single Clingo process, one portfolio-style config, hard wall clock limit (default 600s = 10 min).

Usage: python run_q05_single_10min.py
"""
from __future__ import annotations

import multiprocessing as mp
import queue
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
POL_PATH = HERE.parent / "policy_model.lp"
Q05_PATH = HERE / "q05_center_opening_blue_wins.lp"

# One config (trendy + light randomization — good default for existential search)
CLINGO_OPTS = ["--configuration=trendy", "--rand-freq=0.2"]

WALL_SEC = 600


def _solve(out: mp.Queue, pol_text: str, q_text: str) -> None:
    from clingo import Control

    try:
        c = Control(["-n", "1", "--warn=none", *CLINGO_OPTS])
        c.add("base", [], pol_text + "\n\n" + q_text)
        c.ground([("base", [])])
    except Exception as e:
        out.put(("error", str(e)))
        return
    found = [False]

    def onm(_m):
        found[0] = True

    h = c.solve(on_model=onm)
    if found[0] and h.satisfiable:
        out.put(("sat", ""))
    elif h.unsatisfiable:
        out.put(("unsat", ""))
    else:
        out.put(("unknown", repr(h)))


def main() -> int:
    pol_text = POL_PATH.read_text(encoding="utf-8")
    q_text = Q05_PATH.read_text(encoding="utf-8")
    print(
        f"policy={POL_PATH.name}  query={Q05_PATH.name}\n"
        f"opts={' '.join(CLINGO_OPTS)}\n"
        f"wall_limit={WALL_SEC}s ({WALL_SEC // 60} min)\n",
        flush=True,
    )

    ctx = mp.get_context("spawn")
    q: mp.Queue = ctx.Queue()
    proc = ctx.Process(target=_solve, args=(q, pol_text, q_text))
    t0 = time.perf_counter()
    proc.start()
    proc.join(WALL_SEC)
    elapsed = time.perf_counter() - t0

    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        msg = f"RESULT: TIMEOUT (no sat/unsat within {WALL_SEC}s wall clock)"
        print(msg, flush=True)
        _write_log(msg, elapsed, None)
        return 1

    try:
        kind, detail = q.get_nowait()
    except queue.Empty:
        msg = "RESULT: NO_QUEUE_MESSAGE (child exited without result)"
        print(msg, flush=True)
        _write_log(msg, elapsed, None)
        return 2

    if kind == "error":
        print(f"RESULT: ERROR\n{detail}", flush=True)
        _write_log(f"ERROR: {detail}", elapsed, None)
        return 2
    if kind == "sat":
        print(f"RESULT: SAT (elapsed {elapsed:.1f}s)", flush=True)
        _write_log("SAT", elapsed, "sat")
        return 0
    if kind == "unsat":
        print(f"RESULT: UNSAT (elapsed {elapsed:.1f}s)", flush=True)
        _write_log("UNSAT", elapsed, "unsat")
        return 0
    print(f"RESULT: UNKNOWN {detail}", flush=True)
    _write_log(f"UNKNOWN {detail}", elapsed, None)
    return 3


def _write_log(summary: str, elapsed: float, result: str | None) -> None:
    log = HERE / "q05_single_10min_run.txt"
    log.write_text(
        f"timestamp_utc≈run_script\n"
        f"elapsed_sec={elapsed:.1f}\n"
        f"wall_limit_sec={WALL_SEC}\n"
        f"config={' '.join(CLINGO_OPTS)}\n"
        f"query={Q05_PATH.name}\n"
        f"outcome={summary}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
