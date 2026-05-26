# Temporal surrogates addendum (in scope — no new templates)

Pivot checks **one world** (variable assignment). “Before”, “then”, and “in order” mean **constraints on that snapshot**: ordered scalars, prerequisite booleans, finite phase ints, and implication chains — **not** LTL/CTL, event logs, or multi-step simulation.

Use **only** existing `template_class` values (core eight + vNext where noted). When NL clearly matches a row below, **encode it** — do **not** respond `ABORT` or dilute order into vague prose.

Full NL examples: `temporal_surrogates_examples.md`. Author catalog: repo-root `improved-scope.md` Part G.

## Pattern quick map (T1–T8)

| ID | English cue | Templates | Line split |
|----|-------------|-----------|------------|
| **T1** | Scalar “before” / rank order (`start_x` before `start_y`) | `VARIABLE_RELATIONAL` (`LT`/`LTE`/`GT`/`GTE`) | 1 line |
| **T2** | “B only if A” / gated obligation | `LOGICAL_IMPLICATION` (guard → obligation); optional `CONSTANT_RELATIONAL` on flags | 1–2 lines |
| **T3** | Total order A→B→C on completion flags | `LOGICAL_IMPLICATION` × (n−1): “if B complete then A complete”, … | **n−1 lines** — never one blob |
| **T4** | Finite workflow phase / stage | `SET_INCLUSION` or `INT_RANGE` on `phase`; `EXHAUSTIVE_SWITCH` (vNext) or per-phase `LOGICAL_IMPLICATION` | 2+ lines |
| **T5** | Exactly one active mode/stage | `EXCLUSIVE_CHOICE` (`exactly_one` / `at_most_one`) | 1 line (+ implications per mode if needed) |
| **T6** | At least k of n checks | `K_OF_N` (vNext, n≤10) preferred | 1 line (or split + K_OF_N) |
| **T7** | Rules depend on `workflow_state` / phase | `TABLE_BLOCK` / `DECISION_TABLE_ROW` (vNext) or one `LOGICAL_IMPLICATION` per row | 1 per row or 1 table |
| **T8** | Retry/deadline as int counter | `INT_RANGE` (vNext) or `CONSTANT_RELATIONAL` pair | 1 line |

## Variable naming

- Booleans / 0–1 ints: `step_a_complete`, `identity_verified`, `refund_may_be_issued`.
- Order scalars: `start_`, `rank_`, `deadline_` prefixes.
- Phases: **int-coded** `phase` (1=init, 2=review, …), not unbounded strings.

## Scope rewriter / WFM

For `temporal_or_process_order` lines: rewrite to **state-shaped** lines per table above; **do not** summarize away order. Tag for human review if needed, but keep named flags/ints. Record optional sidecar `temporal_surrogate_applied`: `{ "line_index", "pattern_id": "T1"|…|"T8" }`.

## Extract / repair

- **T1:** `VARIABLE_RELATIONAL` with explicit `left_variable`, `right_variable`.
- **T2–T3:** `LOGICAL_IMPLICATION`; T3 needs **separate NL lines** → separate rules.
- **T4/T6/T7/T8** with vNext: respect caps; set policy envelope **1.1** + `pivot_ir_extensions: ["vnext_8"]` when vNext appears.
- Repairer / tester: compare NL to **assessment** linearization (pre-lowering); do not delete prerequisite chains or scalar order.

## Anti-patterns (still ABORT or rewrite)

- “Events a, b, c in order” with **no** named flags.
- “Within 30 days” without `days_since_event` int.
- LTL (“eventually”, “until”, “always”).
- Calendar strings without int surrogate.
