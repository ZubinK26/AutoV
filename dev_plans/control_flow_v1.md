# NL→Z3 Pipeline — Control Flow (v1)

## Purpose of this document

This document defines the end-to-end control flow for the NL→Z3 formalization pipeline, v1. It is the contract between the WFM stage (upstream, assumed complete) and the formalizer / registry agent / commit stages (downstream, defined here).

**Intent:** LLM-first implementation with **programmatic gates** at named checkpoints. No full Z3-Python grammar validator in v1; **progressive hardening** via sandbox policy, JSON schema, naming rules, and a **deterministic Z3 string extractor** (see below).

**Scope of logic** (target expressiveness): decidable many-sorted FOL per `pipeline_spec.md` (enums, equality, connectives, bounded quantifiers, declared functions with known signatures, bounded integer arithmetic, cardinality constraints where applicable). No transitive closure, no recursion, no temporal reasoning, no higher-order, no unbounded domains.

---

## Semantics: isolated line theories (v1)

**Each IN_SCOPE line is checked in its own self-contained Z3 script.** Assertions from **line A** are **not** automatically combined with **line B** in a single solver state. The **bundle** is linked **documentationally** through the **registry** (shared `entry_id`s, `bundle_id`, `line_index`), not through one merged Z3 model over the whole bundle.

**Cross-line entailment** (“does the full story prove the conclusion?”) is **out of scope** for v1.

---

## Key design decisions (fixed for v1)

1. **Order: WFM → Formalizer → Sandbox → Registry agent → Validation gate → Commit.** The formalizer uses the WFM bundle **only** (registry-blind). The registry agent runs **after** executable Z3 exists.

2. **Registry agent is an LLM with tool access.** Tools: `exact_lookup(canonical_name)`, `signature_lookup(...)`, `semantic_search(text, k)` — backed by the same **`SemanticIndex`** / embedding story as `registry_stage` (e.g. BGE + FAISS; **one** configured model id for the project).

3. **Registry** is queryable memory: identifier standardization and (later) contradiction-oriented retrieval. v1 uses **`entry_refs`** per rule; **labeled graph edges** are deferred.

4. **Strict naming (Rules A–G)** applies to **`canonical_name`** stored in the registry and to **new** proposals in registry-agent JSON. **Not** to arbitrary Python variable names in code (see **Z3 string extractor**).

5. **No user-facing escalation in v1.** Tractable failures use **repair loops**; otherwise the line fails with a **structured category**.

6. **Per-line rule granularity.** Each IN_SCOPE line becomes one **rule** with immutable `rule_id`; the bundle has `bundle_id`; `line_index` preserves order.

7. **Commit-successes policy.** Successful lines **commit**; failed lines are listed with reasons. **No rollback** of successes. **No** user approval gate in v1.

8. **Formalizer retry discards registry-agent work for that line.** If the formalizer emits new code, the registry agent **restarts** for that line from scratch.

---

## Solver outcome vs execution failure (critical)

| Event | Formalizer repair? | Line may continue? |
|-------|----------------------|---------------------|
| **Execution failure:** Python exception, process non-zero exit, **timeout**, missing `check()`, forbidden import or side effect (sandbox policy) | **Yes** (bounded) | After **pass** |
| **Clean exit** with `check()` returning **`sat`**, **`unsat`**, or **`unknown`** | **No** | **Yes** — outcome is **recorded**, not treated as a bug by default |

**Always record** `z3_check_result: sat | unsat | unknown` on the line artifact.

**`unsat` is not** automatically a formalization error: it may be a correct encoding of an inconsistent or tight theory in isolation. **Repair** only when the **process** fails, not when the **solver** returns `unsat`.

**Optional later (not required in v1):** a handoff flag `expect_sat` per line to **fail** or **repair** when `z3_check_result != sat` — omitted here to avoid extra surface area.

---

## Registry naming rules (Rules A–G)

Hard constraints, **programmatically** checkable on **`canonical_name`** (and proposed new names). **Order:** apply **Rule G** (normalize) **before** testing **Rule B** so duplicate proposals collapse; **committed** names remain **ASCII snake** per **B**.

- **Rule A — Global uniqueness.** `canonical_name` is unique across the registry **by kind** as specified (sort / constant / function). No namespacing in v1.

- **Rule B — Regex.** `canonical_name` matches `^[a-z][a-z0-9_]*$` (ASCII snake_case only).

- **Rule C — Kind disjoint.** A sort, constant, and function cannot share the same `canonical_name`.

- **Rule D — Coverage (updated).** Every **Z3 name string** extracted from the line’s code (see **Extractor**) appears in **`symbol_bindings`** for that line, and each binding resolves to **reuse** an existing `entry_id` or **declare** a new entry with valid **`canonical_name`**. **Python** identifiers **not** passed to Z3 as string literals are **out of scope** for Rule D **unless** optional “shadowing check” is enabled (default **off** in v1).

- **Rule E — No function overloading.** Same as before: one `canonical_name` per function signature story in global namespace.

- **Rule F — Flat constants.** Constants use globally unique `canonical_name`; `parent_sort` is metadata.

- **Rule G — Normalize before duplicate checks.** NFC + casefold for **proposals**; then **B** must pass. **Committed** `canonical_name` is ASCII-only.

**A–G do not** require the **same** Z3 string literal on **different** lines for the **same** real-world entity; **reuse** of `entry_id` links semantics. **Per-line** literals may differ until a future optional **rewrite** pass (not v1).

---

## Z3 string extractor (deterministic, not LLM)

**Purpose:** Emit the set of **string literals** used as Z3 symbol names in **`DeclareSort('…')`**, **`Function('…', …)`**, **`Const('…', …)`** (and any other **allowed** constructors listed in implementation). **Implementation** maintains an explicit **allowlist** of AST patterns.

**Rules A–G apply to registry `canonical_name`**, not to forcing **Z3 literals** to match regex **B** — literals must only **appear** in **`symbol_bindings`** and map to a **canonical** row.

---

## Symbol bindings (per line, required)

The registry agent outputs **`symbol_bindings`**: a list covering **every** extracted `z3_string_literal` for that line. Each row includes at minimum:

| Field | Meaning |
|-------|---------|
| `z3_string_literal` | String as it appears in **Z3** API calls for this line |
| `decision` | `reuse_existing` \| `declare_new` |
| `target_entry_id` | If reuse |
| `proposed_canonical_name`, `kind`, `signature` / `parent_sort`, `nl_description` | If declare (subject to A–G) |

**Reuse** of the same `entry_id` across lines is allowed even when **`z3_string_literal`** differs (e.g. `michael` vs `Michael` in literals — **extractor** captures actual strings).

---

## Registry schema (v1, minimum)

**Entries** — keyed by immutable `id`:

| Field | Type | Notes |
|-------|------|------|
| `id` | string | Immutable, system-generated. Never recycled (tombstone if removed). |
| `kind` | enum | `sort` \| `constant` \| `function` |
| `canonical_name` | string | Rules A–G |
| `signature` | object | Functions: domains, codomain, arity |
| `parent_sort` | string | Constants |
| `nl_description` | string | Short NL |
| `source_rule` | list[string] | Rule IDs |
| `embedding` | vector | From `canonical_name` + `nl_description` per project embedding config |

**`members` (sorts):** **Not** dual-written in v1. **Derive** at read from constants’ `parent_sort`, **or** compute once at commit in the same transaction.

**Rules** — one per IN_SCOPE line that shipped:

| Field | Type | Notes |
|-------|------|------|
| `rule_id` | string | Immutable |
| `bundle_id` | string | |
| `line_index` | int | |
| `statement_nl` | string | WFM lineage |
| `z3_code` | string | Accepted source |
| `z3_check_result` | enum | `sat` \| `unsat` \| `unknown` |
| `entry_refs` | list[string] | Entry IDs used |
| `symbol_bindings` | list[object] | Validated copy of resolved bindings |

**Bundles** — per acceptance:

| Field | Type | Notes |
|-------|------|------|
| `bundle_id` | string | |
| `rule_ids` | list | Ordered |
| `accepted_at` | timestamp | UTC |
| `pipeline_status` | enum | `committed` \| `partially_committed` \| `failed` |
| `failed_lines` | list | `{line_index, reason_category, reason_text, budget_log?}` |

**Persistence:** `registry.json`, `rules.json`, `bundles/{bundle_id}.json`; single writer; atomic commit (staged write + rename).

**Deferred:** labeled graph edges, rule-level embeddings, `committed_edges` enum.

---

## Programmatic validation gate (sequence)

1. **JSON schema** — registry agent output valid.
2. **Extractor ⊆ bindings** — every extracted Z3 string has a **binding** row.
3. **Rules A–G** — all **proposed** / **new** `canonical_name` values.
4. **Reuse verification** — `target_entry_id` exists; **signature** matches usage.
5. **Ambiguity (validator-owned)** — for each **declare_new** (or optionally reuse), **validator** calls **`semantic_search`** with a **deterministic query** (e.g. `proposed_canonical_name + "\n" +` snippet from `statement_nl` or `nl_description`). If **top two** hits **both** ≥ `similarity_floor` **and** **|score1 − score2| ≤ delta`**, require JSON fields **`chosen_from_candidates`** or **`justify_new_despite_near_duplicate`**; else **fail** with **top-k** listed for repair.

**Implementation constants** (`similarity_floor`, `delta`, `top_k`) are **open items** below.

---

## Control flow (diagram)

```
WFM bundle
    │
    ▼
Partition lines (IN_SCOPE / OUT_OF_SCOPE)
    │
    ▼ IN_SCOPE only
Formalizer (LLM) ──► per-line self-contained z3_code (import z3; z3.*)
    │
    ▼
Sandbox (whitelist z3, timeout, no network)
    │
    ├─ execution FAIL ──► Formalizer repair (bounded) ──► retry or Z3_FAIL
    │
    └─ execution OK ──► record z3_check_result (sat|unsat|unknown) ──► proceed
    │
    ▼
Registry agent (LLM + tools) ──► symbol_bindings + metadata JSON
    │
    ▼
Validation gate (checks 1–5)
    │
    ├─ fail ──► Registry agent repair (bounded) ──► retry or REGISTRY_*
    │
    └─ pass ──► Commit (atomic)
    │
    ▼
Terminal bundle state
```

**Budgets (suggested defaults — tune in implementation):**

- Formalizer repair: **1–5** per line.
- Registry agent repair: **3** per line.
- **Global per-line cap:** **10** total iterations across **formalizer + registry + validation** repair loops.
- **Budget log (required):** `formalizer_attempts`, `registry_attempts`, `validation_attempts` per line.

---

## Failure categories

| Category | Meaning |
|----------|---------|
| `Z3_FAIL` | **Execution** failure after formalizer budget exhausted (exception, timeout, policy violation, missing `check()`, etc.) — **not** `unsat` alone |
| `REGISTRY_SCHEMA` | JSON invalid after repair budget |
| `REGISTRY_NAMING` | A–G violations after repair budget |
| `REGISTRY_REUSE_INVALID` | Reuse claim inconsistent with registry |
| `REGISTRY_AMBIG` | Ambiguity check 5 failed after repair |
| `BUDGET_EXHAUSTED` | Global cap hit |

---

## Empty registry, OUT_OF_SCOPE, non-goals

- **Empty registry:** tools return empty; agent **declares new**; A–G still apply among **new** proposals in the transaction.
- **OUT_OF_SCOPE:** skip formalizer/registry/commit for rule rows; **no** `rule_id`; metadata only.

**v1 does not include:** user review UI, graph edges, rule embeddings, **merged** multi-line Z3 theory, contradiction engine, cross-bundle audit, structured IR, **optional** `expect_sat` (unless added later).

---

## Open items (parameters only)

1. Formalizer repair cap (pick **1–5**).
2. Registry repair cap (default **3**).
3. Global per-line cap (default **10**).
4. Sandbox timeout (ms).
5. `semantic_search` **k** for agent and validator.
6. **`similarity_floor`** and **`delta`** for ambiguity.
7. **Exact JSON Schema** for registry agent output (including `symbol_bindings`).
8. Atomic commit mechanism.
9. **Log line** per repair iteration with **sub-counters**.

---

## Stage I/O

**Formalizer input:** IN_SCOPE lines; **prompt** may include **A–G** as **text**; **no** registry.  
**Formalizer output:** `z3_code` per line; **style:** `import z3` and `z3.` prefix (recommended).

**Registry agent input:** `z3_code`, `statement_nl`, tools.  
**Registry agent output:** `symbol_bindings` + fields required for **schema** + **commit**.

**Commit input:** validated JSON + `z3_code` + WFM metadata + registry state.  
**Commit output:** updated JSON files + `pipeline_status`.

---

## End of specification
