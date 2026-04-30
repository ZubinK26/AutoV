"""Run query_*.lp against policy_model.lp in parent dir; write *_result.txt. Does not modify policy."""
from __future__ import annotations

import hashlib
from pathlib import Path

from clingo import Control

HERE = Path(__file__).resolve().parent
POL = (HERE.parent / "policy_model.lp").resolve()


def main() -> None:
    before = hashlib.sha256(POL.read_bytes()).hexdigest()
    pol = POL.read_text(encoding="utf-8")
    queries = [
        ("query_safety", "query_safety.lp"),
        ("query_blocking", "query_blocking.lp"),
        ("query_liveness", "query_liveness.lp"),
    ]
    for name, qf in queries:
        qtext = (HERE / qf).read_text(encoding="utf-8")
        out: list[str] = []
        # "0" means enumerate all answer sets; for large programs the solver may not finish.
        c = Control(["-n", "1", "--warn=none"])
        try:
            c.add("base", [], pol + "\n\n" + qtext)
            c.ground([("base", [])])
        except Exception as e:  # noqa: BLE001
            out.append(f"GROUND_ERROR: {e}")
            (HERE / f"{name}_result.txt").write_text("\n".join(out), encoding="utf-8")
            continue
        mdl = [None]

        def onm(m):
            mdl[0] = m

        h = c.solve(on_model=onm)
        if h is None:
            out.append("RESULT: NO_SOLVE_RESULT")
        elif h.unsatisfiable:
            out.append("RESULT: UNSATISFIABLE")
        elif h.satisfiable and mdl[0] is not None:
            out.append("RESULT: SATISFIABLE (at least one answer set matches query constraints)")
            out.append("")
            out.append("SAMPLE_ANSWER_SET (first model):")
            out.append(str(mdl[0]))
        else:
            out.append(f"RESULT: UNKNOWN  satisfiable={h.satisfiable}  unsat={h.unsatisfiable}")
        (HERE / f"{name}_result.txt").write_text("\n".join(out), encoding="utf-8")
    after = hashlib.sha256(POL.read_bytes()).hexdigest()
    (HERE / "policy_model_sha256_verification.txt").write_text(
        f"policy_model.lp SHA-256 before runs: {before}\n"
        f"policy_model.lp SHA-256 after runs:  {after}\n"
        f"unchanged: {before == after}\n",
        encoding="utf-8",
    )
    print(before, after, before == after)


if __name__ == "__main__":
    main()
