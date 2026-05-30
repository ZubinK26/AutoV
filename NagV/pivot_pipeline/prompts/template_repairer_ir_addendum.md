# Template Repairer IR addendum

## `repair_strategy` on handoff findings (server-assigned)

| `repair_strategy` | Required direction |
|-------------------|-------------------|
| `counterfactual_avoid_implication_on_mutant_pins` | No `LOGICAL_IMPLICATION` with `is_candidate` / `applicant_position` trigger on cited rules |
| `counterfactual_require_enforced_obligation` | `K_OF_N` + non-empty `result_variable` (Way B); same implication ban as above |
| `vacuous_k_of_n_enforce` | `K_OF_N` + `result_variable`; no role-triggered implication as sole enforcement |
| `template_golden_no_ir` | No IR change |

## Finding → edit patterns

| Category | Allowed edits |
|----------|----------------|
| `policy_vs_nl`, `vacuous_k_of_n` | `K_OF_N` with `result_variable`; optional `CONSTANT_RELATIONAL` requiring aggregate true for global lines |
| `variable_collision` | Distinct `result_variable` per rule |
| `trigger_inconsistency` | Remove `is_candidate` / role triggers; make obligations global |
| `template_golden`, `template_world` | **No IR change** unless finding wrongly blamed — prefer no-op |

## K_OF_N (Way B)

- One NL line → one `rule_id` with `K_OF_N` + `result_variable`.
- Do not append companion rules unless `allow_append_rules` is true.
- Do not put `k_of_n` inside `LOGICAL_IMPLICATION` trigger trees.

## Template semantics (for alignment)

- Lowered k-of-n: `Implies(at_least_k(clauses), result==true)` — when no clause is true, the rule is vacuously satisfied; an NL obligation that must hold needs the aggregate (or equivalent) to **constrain outcomes**, not only assign a boolean.
- After adding `result_variable` on `K_OF_N`, verify in `linearized_excerpt` that lowering/enforcement is present (`enforcement: via compile lowering` or a global rule that requires the aggregate). A `result_variable` that nothing uses is incomplete.

## Anti-patterns (executor-level)

| Pattern | Typical suite symptom | Prefer instead |
|---------|----------------------|----------------|
| `LOGICAL_IMPLICATION` with role/world trigger + `required_condition` on the same fact the **mutant** flips false while trigger stays true | `counterfactual_flip` **inconclusive** (mutant UNSAT / null decision), not unsatisfied | Obligation encoding where mutant pins yield **unsatisfied** without making the whole world inconsistent |
| `K_OF_N` + `result_variable` with no global enforcement | `counterfactual_flip` **fail** (mutant still satisfied) | Way B complete: aggregate enforced for in-scope NL |
| Duplicate `result_variable` across rules | Variable collision / ambiguous pathway | Distinct aggregate per obligation |

## Encoding choice (when findings conflict)

- If an approved finding mentions **UNSAT** on a counterfactual mutant, do **not** “fix” it by switching to an unenforced `K_OF_N` assign-only shape.
- If a finding mentions **vacuous** or **still satisfied** on mutant, do **not** “fix” it by adding a hard implication that contradicts mutant pins.
- Resolve toward: NL obligation enforced **and** `counterfactual_flip` can observe satisfied → unsatisfied on the cited query/rule.
