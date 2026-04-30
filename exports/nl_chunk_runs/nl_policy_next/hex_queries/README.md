# Hex policy queries (ASP)

Formalizations of the NL questions against `../policy_model.lp`.

**Predicates used** (from policy): `wins/2`, `occurs/3`, `time/1`, `player/1`, `located_on/3`, `game_over/1`.

**Query 4 note:** Natural language says blue plays **optimally** to stop red. The policy has no minimax / optimality; `q04_...` only fixes red’s first move at (3,3) and asks whether **some** legal play exists where red wins by turn 25.

## How to run

From repo root (or this folder):

`python exports/nl_chunk_runs/nl_policy_next/hex_queries/run_hex_queries.py`

Uses `--configuration=jumpy` and a **90s wall-clock limit per query** (multiprocessing). Existential Hex search can exceed that; see `results_hex_queries.txt`.

## Empirical results (this machine)

| # | File | Clingo outcome |
|---|------|----------------|
| 1 | `q01_neither_wins_completion.lp` | **UNSAT** (~8s without timeout) — aligns with policy rule “no draw at time 25” forcing `game_over(25)` |
| 2 | `q02_red_wins_by_turn_25.lp` | **SAT** |
| 3 | `q03_blue_wins_by_turn_25.lp` | **TIMEOUT** at 90s; longer attempt did not finish — **not** proven SAT/UNSAT here |
| 4 | `q04_red_center_red_wins_optimal_note.lp` | **SAT** (optimal blue **not** modeled; see file header) |
| 5 | `q05_center_opening_blue_wins.lp` | **TIMEOUT** at 90s |

Each file is designed for: `clingo -n 1 policy_model.lp q0X_...lp`.
