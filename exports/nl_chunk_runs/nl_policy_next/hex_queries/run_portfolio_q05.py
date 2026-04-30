"""
Parallel portfolio for q05 only (red center + symmetry-broken blue first move).

Uses a *small* worker count (4) to limit CPU contention vs many parallel Clingo instances.
Each process: different --configuration and --rand-freq until one finds SAT or time budget.
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

# Four workers only: fewer concurrent heavy solves → less oversubscription (ease CPU contention).
# Heuristic presets × --rand-freq in [0,1] (fraction, not percent).
PORTFOLIO: list[list[str]] = [
    ["--configuration=jumpy", "--rand-freq=0.0"],
    ["--configuration=jumpy", "--rand-freq=0.35"],
    ["--configuration=trendy", "--rand-freq=0.2"],
    ["--configuration=frumpy", "--rand-freq=0.15"],
]

# Per-worker wall clock (seconds); each runs in parallel
TIMEOUT_SEC = 300


def _worker(opts: list[str], pol_text: str, q_text: str, worker_id: int, out: mp.Queue) -> None:
    from clingo import Control

    try:
        c = Control(["-n", "1", "--warn=none", *opts])
        c.add("base", [], pol_text + "\n\n" + q_text)
        c.ground([("base", [])])
    except Exception as e:
        out.put((worker_id, "error", str(e)))
        return
    found = [False]

    def onm(_m):
        found[0] = True

    h = c.solve(on_model=onm)
    if found[0] and h.satisfiable:
        out.put((worker_id, "sat", " ".join(opts)))
    elif h.unsatisfiable:
        out.put((worker_id, "unsat", " ".join(opts)))
    else:
        out.put((worker_id, "unknown", " ".join(opts)))


def main() -> int:
    pol_text = POL_PATH.read_text(encoding="utf-8")
    q_text = Q05_PATH.read_text(encoding="utf-8")
    print(f"policy={POL_PATH}  query={Q05_PATH}  workers={len(PORTFOLIO)}  timeout={TIMEOUT_SEC}s each")
    sys.stdout.flush()

    ctx = mp.get_context("spawn")
    out: mp.Queue = ctx.Queue()
    procs: list[mp.Process] = []
    t0 = time.perf_counter()
    for i, opts in enumerate(PORTFOLIO):
        p = ctx.Process(target=_worker, args=(opts, pol_text, q_text, i, out))
        p.start()
        procs.append(p)

    sat_opts = None
    errors: list[str] = []
    deadline = t0 + TIMEOUT_SEC + 120

    while time.perf_counter() < deadline:
        try:
            wid, kind, detail = out.get(timeout=2.0)
            print(f"[worker {wid}] {kind}: {detail}")
            sys.stdout.flush()
            if kind == "sat":
                sat_opts = detail
                break
            if kind == "error":
                errors.append(detail)
        except queue.Empty:
            if not any(p.is_alive() for p in procs):
                try:
                    wid, kind, detail = out.get_nowait()
                    print(f"[worker {wid}] {kind}: {detail}")
                    if kind == "sat":
                        sat_opts = detail
                except queue.Empty:
                    pass
                if sat_opts:
                    break
                break
        if time.perf_counter() - t0 > TIMEOUT_SEC + 30 and not sat_opts:
            for p in procs:
                if p.is_alive():
                    p.terminate()
            break

    if sat_opts:
        print(f"\nRESULT: SAT  (portfolio: {sat_opts})")
        for p in procs:
            if p.is_alive():
                p.terminate()
            p.join(2)
        print(f"elapsed_wall={time.perf_counter() - t0:.1f}s")
        return 0

    for p in procs:
        if p.is_alive():
            p.join(timeout=max(0, TIMEOUT_SEC - (time.perf_counter() - t0) + 5))
    for p in procs:
        if p.is_alive():
            p.terminate()
        p.join(2)

    # Drain queue
    while not out.empty():
        try:
            print(f"[late] {out.get_nowait()}")
        except Exception:
            break

    el = time.perf_counter() - t0
    if errors and sat_opts is None:
        print(f"\nRESULT: ERROR  {errors}")
        return 2
    print(f"\nRESULT: no SAT witness within {TIMEOUT_SEC}s parallel portfolio window")
    print(f"(Workers finished or timed out; this is not a proof of UNSAT.)")
    print(f"elapsed_wall={el:.1f}s")
    return 1


if __name__ == "__main__":
    mp.freeze_support()
    raise SystemExit(main())
