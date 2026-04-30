"""Run ranked scenario-pinned violation queries; overwrite results file."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from clingo import Control

HERE = Path(__file__).resolve().parent
POL = (HERE.parent / "policy_model.lp").read_text(encoding="utf-8")
RESULTS = HERE / "conditions_query_results.txt"

RUNS = [
    ("rank01_nl28_grappled_speed.lp", "NL#28 grappled speed 0"),
    ("rank02_nl61_restrained_speed.lp", "NL#61 restrained speed 0"),
    ("rank03_nl55_poisoned_attack_disadv.lp", "NL#55 poisoned attack disadvantage"),
    ("rank04_nl18_exhaustion_cap_death.lp", "NL#18 exhaustion 5+2 cap at 6 and die"),
    ("rank05_nl86_paralyzed_incapacitated.lp", "NL#86 paralyzed inherits incapacitated"),
    ("rank06_nl84_blinded_two_instances_one_expired.lp", "NL#84 blinded persists while second instance active"),
    ("rank07_nl25_frightened_no_los_ability_disadv.lp", "NL#25 frightened without LOS no ability-check disadv"),
    ("rank08_nl20_remove_exhaustion_falls_below_one.lp", "NL#20 remove 2 from level 1 clamps to 0"),
]


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines_out = [
        "conditions_query_results.txt — scenario-pinned violation queries\n",
        "Pattern: pins + viol + :- not viol.  SAT => violation exists; UNSAT => consequent forced.\n",
        f"=== run {stamp} ===\n\n",
    ]
    for fname, label in RUNS:
        qpath = HERE / fname
        qtext = qpath.read_text(encoding="utf-8")
        c = Control(["-n", "1", "--warn=none"])
        try:
            c.add("base", [], POL + "\n\n" + qtext)
            c.ground([("base", [])])
        except Exception as e:
            lines_out.append(f"{fname} ({label})\n  GROUND_ERROR: {e}\n\n")
            print(f"{fname} GROUND_ERROR: {e}")
            continue
        h = c.solve()
        if h.unsatisfiable:
            cls = "UNSAT"
            note = "no violation witness — consequent enforced for pinned scenario (policy passes this check)"
        elif h.satisfiable:
            cls = "SAT"
            note = "violation witness exists — pinned scenario allows consequent to fail (policy gap / unpinned interaction)"
        else:
            cls = "UNKNOWN"
            note = str(h)
        block = f"{fname} ({label})\n  result={cls}\n  interpretation: {note}\n\n"
        lines_out.append(block)
        print(block, end="")

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text("".join(lines_out), encoding="utf-8")
    print(f"Overwrote {RESULTS}")


if __name__ == "__main__":
    main()
