# Condition-rule queries — formalization standard

Two acceptable shapes (you must know which one you are running):

---

## Form 1 — Scenario-pinned violation witness (**used for rank01–rank03 runs**)

1. **Ground the antecedent** as hard facts: named creatures, `time(...)`, and `holds(condition(...), ...)`.
2. Define **`viol`** as “antecedent holds but consequent fails” (e.g. grappled but speed not 0, or missing `holds(speed,0)`).
3. Add **`:- not viol.`** so the task is to derive `viol` if possible.

**Read results:**

| Result | Meaning |
|--------|--------|
| **SAT** | A violation exists (pinned scenario + policy allows consequent to fail) → **policy did not enforce** the rule for that scenario. |
| **UNSAT** | No violation; consequent is forced for the pinned scenario → **rule holds** for that check. |

---

## Form 2 — Global integrity constraint (documentation only unless you switch the `.lp` file)

Forbid bad joint atoms everywhere:

```asp
:- holds(condition(C, grappled(G)), T), holds(speed(C, V), T), V != 0.
```

Interpretation when adding **only** this line (no pins):

- If **every** answer set of the policy **already** avoids that joint pattern, the constraint is **vacuously** satisfied and you still get **SAT** of `P ∪ constraint` — **not** the same test as Form 1.
- Form 1 is preferred for “does my rule fire on this scenario?”

---

## Rank order (easiest structure first)

| Rank | NL# | Form | Notes |
|------|-----|------|--------|
| 1 | 28 | Form 1 | Grappled → speed 0 |
| 2 | 61 | Form 1 | Restrained → speed 0 |
| 3 | 55 | Form 1 | Poisoned → disadvantage on `attack_roll(qc, qb)` at pinned time |

Constants **`qt`** are abstract; Clingo treats them as integers/symbols per grounding — ensure `time(qt)` appears so `time/1` is populated for the scenario if the policy requires it.
