# Dev plan — Bundle merge, joint Z3 theory, registry-aligned formalization (v1)

## Purpose

Extend the product so that, **after** per-line NL→SMT-LIB work exists (today’s `smt_pipeline` per bundle / per policy file), we can optionally run a **bundle-level** step that:

1. Produces a **single merged formalization** (or a well-defined artifact that compiles to one Z3 script) for the **whole** WFM-accepted bundle.
2. Runs **reliable programmatic checks** on that artifact (syntax, sandbox, **joint** `check()`, registry alignment).
3. Uses an **LLM only as a builder** under a **structured contract**; **correctness** of satisfiability is **always** decided by **Z3** (and static validators), not by the model’s prose.

This document **does not** replace `control_flow_v3.md` / `smt_pipeline` per-line semantics; it **adds** an optional downstream phase with explicit scope.

---

## Vision you described (restated precisely)

- **Build:** An LLM (or sequence of calls) consumes **bundle-level context** (WFM NL, per-line Z3 and/or summaries, registry state) and returns **structured output** describing the merged theory (see §5).
- **Check:** We validate that output in every way we **reliably can**; bounded repair on failure.
- **Success:** If checks pass, we treat the **bundle formalization** as **accepted** for this phase (subject to explicit limitations below).
- **Registry:** Symbols in the final theory must **map to registry entries**; vocabulary that does not appear in the final merged theory is **not** part of that bundle’s “closed world” for this step.

**Clarification needed on “nothing new” (see §3):** strict **reuse-only** (no new registry rows during merge) vs **freeze-after-line-commit** (all symbols already committed per line, merge only references existing ids). The plan supports both; **default recommendation** is **freeze-after-line-commit** for v1 merge.

---

## Feasibility and limits (honest)

| Aspect | Verdict |
|--------|---------|
| Joint `sat` / `unsat` / `unknown` on **one** merged script | **Feasible** — Z3 is the oracle; we run one solver after deterministic codegen. |
| LLM proposes merge; tests decide | **Feasible** — standard pattern: **generate → validate → repair**. |
| **Single coherent ontology** across lines written independently | **Hard** — not impossible, but contradictions and sort drift are **expected** until alignment is enforced. |
| **Final theory uses only existing registry entities** | **Feasible** **if** “existing” means **ids already in `RegistrySession` before merge** (from per-line commits or a prior seed). **Not** feasible as “no new symbols anywhere in the product ever” for bundles that introduce new concepts — those must be **registered before** merge or merge must **fail closed**. |
| “Registry entries not in the final theory are **out**” | **Do not** interpret as “delete global registry rows.” **Do** interpret as: **bundle closure**: mark which `entry_id`s are **referenced** by the merged theory / bundle rules; **optional** tombstone or **bundle-scoped** metadata is a **product decision** (see §7). |

**Conclusion:** The vision is **ideal and implementable** as a **checked merge layer**, not as “the LLM proves entailment.” Where it is **weak** is **semantic alignment** across lines; mitigations are **explicit equality/merge map**, **human-in-the-loop** for high-stakes bundles, or **narrower** merge (e.g. only lines that share declared sorts).

---

## Relationship to existing `smt_pipeline` (v3)

- **Keep** per-line / per-bundle SMT-LIB commits via `smt_pipeline` as **Phase A** (current milestone): formalizer + critic + policy file, optional registry elsewhere.
- **Add** optional **Phase B — bundle merge** (this plan): runs **after** Phase A completes (or after a defined checkpoint), consumes **committed** line artifacts + **WFM bundle text** (+ registry snapshot if used), emits **merge artifact** + **joint theory** + **alignment report**.

Phase B **does not** retroactively invalidate Phase A; it **adds** a bundle-level verdict and optional new **bundle_rule** / **merge_record** artifacts.

---

## Goals (v1)

1. **Joint theory check:** One sandbox run of the **merged** Z3 script; record `check()` result and errors.
2. **Deterministic validation:** Parse/AST or string-level checks that the merged script only references **allowed** symbols (see §6).
3. **Structured LLM output:** Versioned JSON schema for “merge plan” or “symbol map + conjoined axioms” (exact shape TBD in design review).
4. **Bounded repair:** Cap on LLM+repair iterations; fail with structured category if exceeded.
5. **Registry alignment mode:** Configurable **`reuse_only`** — merge output must reference **only** `entry_id`s present in session (or explicit `sort`/`fn`/`ent` ids from a supplied list). No shadow `DeclareSort('foo')` unless `foo` maps to an existing sort id **or** merge fails.

## Non-goals (v1)

- Proving **entailment** of the last line from **all** previous lines (theorem proving); only **joint satisfiability** of the **asserted** merged theory unless you explicitly add a **proof obligation** later.
- Automatic **ontology alignment** without an LLM or without user confirmation — possible as v2.
- Deleting unused global registry entries automatically.

---

## Architecture (high level)

```
WFM HandoffBundle
       │
       ▼
[Phase A] smt_pipeline (per bundle / policy file) ──► SMT-LIB + bundle JSON (+ optional registry session)
       │
       ▼
[Phase B] Bundle merge service (NEW)
  Inputs:
    - confirmation / Style-A NL (bundle-level story)
    - For each line: statement_nl, z3_code (or hash + fetch), symbol_bindings trace, rule_id
    - Registry snapshot: entry_id → kind, name, signatures
  LLM:
    - Emits MERGE_ARTIFACT (JSON): symbol correspondence, ordering, optional skolemization notes, single script OR layered defs + single assert block
  Deterministic builder:
    - Compiles MERGE_ARTIFACT → z3_merge.py (or emits Python source string)
  Gates:
    - static: allowed names/ids only
    - sandbox: run merged script once
    - z3: capture sat/unsat/unknown
  Output:
    - bundle_merge_status, joint_z3_check_result, referenced_entry_ids, errors
```

---

## MERGE_ARTIFACT (conceptual; schema to be fixed in implementation)

Minimum concepts to include (names illustrative):

- `schema_version`: `bundle_merge_v1`
- `referenced_registry_entry_ids`: list[str] — **must** cover every logical symbol used.
- `z3_source`: str — **or** a declarative list of **steps** if we forbid free-form Python in v1.
- `symbol_map`: optional — maps Z3 string names → `entry_id` (for audit).
- `notes`: optional human-readable merge rationale (not validated except length).

**Implementation decision:** Prefer **templated codegen** from MERGE_ARTIFACT (deterministic Python from JSON) over trusting the LLM to paste arbitrary Python for v1; if the LLM only fills **ids + ordering + which axioms concatenate**, injection and drift risk drop.

---

## Validation layers (all that we “reliably can”)

1. **JSON schema** — MERGE_ARTIFACT parses; required fields present.
2. **Registry closure** — every referenced `entry_id` exists and is `active`; kinds match usage (sort vs fn vs const).
3. **Arity / sort signature check** — function applications match `domain_sort_ids` / `codomain_sort_id` from registry (requires loading `RegistryEntry` for each id).
4. **No undeclared string literals** — optional: cross-check against extractor allowlist of **only** registry-backed names (strict mode).
5. **Sandbox policy** — same as today: timeout, imports, `check()` present.
6. **Z3** — `sat` / `unsat` / `unknown` recorded; optional model pretty-print dev-only.

**Repair loop:** On failure categories `MERGE_SCHEMA`, `MERGE_REGISTRY_CLOSURE`, `MERGE_SIGNATURE`, `Z3_FAIL`, feed last error + artifact back to LLM with **tight** repair prompt; cap `N` attempts.

---

## “Only existing registry entities” — operational definition (recommended)

**Mode A — Strict (recommended for v1):**

- Per-line Phase A has already created **all** needed `sort_` / `ent_` / `fn_` rows for symbols that may appear in the bundle.
- Phase B **must not** call `commit` for **new** entries; it only **references** ids.
- If the merged theory needs a symbol **not** in registry → **MERGE_INCOMPLETE** (fail closed) or explicit **gap list** for a human/registry sub-step.

**Mode B — Relaxed (optional later):**

- Allow merge to output **new** declarations, then **auto-register** — contradicts “nothing new” unless you redefine “new” as “after merge commit” only.

Default dev plan: **Mode A**.

---

## “Entries not in the final theory are out”

**Recommended interpretation (v1):**

- Compute `referenced_ids` from MERGE_ARTIFACT + static analysis of generated Z3.
- Persist **`bundle_referenced_entry_ids`** on a **bundle merge record** (sidecar JSON or rules metadata).
- **Do not** auto-tombstone global registry entries merely because one bundle’s merged theory omits them — other bundles may still need them.

Optional later: “bundle closure report” listing **unreferenced** ids **among** ids introduced by **this** bundle’s lines (lineage tracking) — requires **provenance** on entries (`source_rule` already partially there).

---

## Phasing

| Milestone | Deliverable |
|-----------|-------------|
| **M0** | This doc + schema sketch for MERGE_ARTIFACT + failure categories |
| **M1** | Deterministic validator: registry closure + signature check for a **hand-built** MERGE_ARTIFACT (no LLM) |
| **M2** | Deterministic codegen from MERGE_ARTIFACT → one Z3 script; sandbox + joint `check()` |
| **M3** | LLM: bundle context → MERGE_ARTIFACT; repair loop; metrics |
| **M4** | CLI flag / pipeline orchestration: Phase A → optional Phase B; export `bundle_merge.json` |
| **M5** | Tests: toy bundle sat; toy unsat; signature mismatch fails; missing id fails |

---

## Risks

- **Contradictory lines** → joint `unsat`; product must distinguish “merge OK but theory inconsistent” vs “merge invalid.”
- **LLM hallucinated ids** → caught by registry closure if ids are validated strictly.
- **Context limits** on long bundles → chunking merge plan (e.g. by dependency layers) or summarization of per-line Z3 with **loss** (riskier).

---

## Open decisions (to resolve before coding)

1. **Merge input:** Raw concatenation of per-line `z3_code` vs **registry-parameterized** codegen only (recommended: latter for strict mode).
2. **Joint SAT expectation:** Is `unsat` a **failure** for the product, or an **acceptable** outcome with reporting?
3. **Conclusion line:** Include or exclude from **same** merged check vs separate obligation (entailment is non-goal unless specified).
4. **Storage:** Where `bundle_merge` record lives (`rules.json`, `bundles/{id}.pipeline.json`, new table).

---

## Summary

The intent you described — **LLM builds under a contract, we check everything we can, Z3 decides satisfiability, registry vocabulary for the merged theory is closed against existing ids** — is **sound** and **implementable**. It is **not** impossible; the **hard** part is **alignment** across independently generated lines, which is why **strict registry-only merge** plus **deterministic codegen** and **explicit referenced_id lists** are the recommended v1 path. Per-line v1 remains a **useful milestone**: it populates the registry Phase B needs; Phase B is the **bundle-level** quality gate you want next.
