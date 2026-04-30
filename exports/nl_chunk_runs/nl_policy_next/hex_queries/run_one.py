"""Usage: python run_one.py q03_blue_wins_by_turn_25.lp [sec]"""
import sys
import time
from pathlib import Path

from clingo import Control

HERE = Path(__file__).resolve().parent
POL = (HERE.parent / "policy_model.lp").read_text(encoding="utf-8")


def main() -> None:
    qf = HERE / sys.argv[1]
    lim = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0
    q = qf.read_text(encoding="utf-8")
    t0 = time.perf_counter()
    c = Control(["-n", "1", "--warn=none", "--configuration=trendy"])
    c.add("base", [], POL + "\n\n" + q)
    c.ground([("base", [])])
    h = c.solve()
    dt = time.perf_counter() - t0
    print(qf.name, "elapsed", round(dt, 2), "s")
    print("unsat", h.unsatisfiable, "sat", h.satisfiable)


if __name__ == "__main__":
    main()
