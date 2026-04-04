# NL→Z3 Formalization Pipeline — Scope & Architecture

This document describes the end-to-end pipeline. **Well-formedness (WFM)** behavior is defined in **`WFM/Agent_WFM.md`**; where details differ, **`WFM/Agent_WFM.md` takes precedence.**

**WFM config (defaults):** `WFM/config/wfm.json` — e.g. `max_input_code_points` (**4096** by default; see `WFM/Agent_WFM.md` for rationale).

**WFM LLM prompts:** `WFM/prompts/` (per-agent instruction files; see `WFM/prompts/README.md`).

---

## Scope: Decidable Many-Sorted FOL

**Included:**

- Finite declared sets (enums) with explicit membership
  - ✅ "Season is one of: spring, summer, autumn, winter"
  - ❌ "For any real number x..."

- Properties and equality over declared entities
  - ✅ "The status of order A is delivered"
  - ❌ "Product A is similar to product B" (vague, non-formal)

- Boolean connectives: and, or, not at any nesting level
  - ✅ "A vehicle is registered and not scrapped"

- Implication and biconditional
  - ✅ "If a patient is discharged then they are not in a ward"
  - ❌ "A patient eventually recovers" (temporal)

- Bounded quantifiers (∀, ∃) over explicitly declared finite sets only
  - ✅ "For every student S in students: S has an advisor"
  - ❌ "For every possible seating arrangement..."

- Declared functions with known signatures (entity→entity, entity→property, etc.)
  - ✅ "habitat(A) returns a Biome"
  - ❌ "some function of A" (undeclared, unknown signature)

- Nested quantifiers over declared domains
  - ✅ "For every classroom, there exists a teacher assigned to that classroom"
  - ❌ "For every possible route between two cities..." (unbounded/computed)

- Negation at any scope level, including negated quantified statements
  - ✅ "It is not the case that all animals are herbivores"

- Disjoint/exhaustive type constraints (X is exactly one of {A, B, C})
  - ✅ "A traffic light is exactly one of: red, amber, green"
  - ❌ "A light can be red and green simultaneously"

- Bounded integer arithmetic (comparisons, ranges)
  - ✅ "A floor number is between 1 and 50"
  - ❌ "The population grows without bound"

- Cardinality constraints ("exactly N", "at most N")
  - ✅ "Each flight has at most two pilots"
  - ❌ "Most recipes are vegetarian" (vague quantifier)

- Conditional chains (nested if-then)
  - ✅ "If a book is overdue and the borrower is a member, then if the fine exceeds the limit, the borrower is suspended"
  - ❌ "If a book could potentially be returned late..." (hypothetical/computed)

**Excluded:**

- Transitive closure / reachability / recursion
  - ❌ "A supervisor can reach any worker through the chain of command" (requires path reasoning)

- Temporal or state-history reasoning
  - ❌ "If the bridge has never been inspected, it is flagged" (requires history)

- Computed sets (defining a set by a condition, then quantifying over it)
  - ❌ "For all dishes that contain allergens..." (set defined by condition)

- Higher-order logic
  - ❌ "For every attribute that a product can have..." (quantifying over properties)

- Unbounded domains
  - ❌ "For any natural number n..."

- Anything requiring Z3 quantifier instantiation heuristics or triggers
  - ❌ "For all mappings from ingredients to suppliers..." (requires Z3 triggers)

**Benchmark compatibility:** Covers FOLIO and P-FOLIO datasets.

---

## Pipeline

**Pipeline stages (4 top-level agents):**

1. **Well-formedness module (WFM)** — internal **four** sub-agents (see `WFM/Agent_WFM.md` and `WFM/prompts/`).
2. **Registry agent** (extract → search → resolve with user → populate)
3. **Formalizer**
4. **Identifier critic**

**LLM:** Claude API for all LLM-driven stages (including all WFM sub-agents).

### Steps:

1. **User input** — natural language rule, unrestricted phrasing. **Safety:** before WFM, enforce **`max_input_code_points`** from `WFM/config/wfm.json` (default **4096** Unicode code points). If over limit, return to input with counts vs. limit; no auto-chunking. See `WFM/Agent_WFM.md`.

2. **Well-formedness module (WFM)** — Runs **Agent 1 → Agent 2 → Agent 3 → Agent 4** as specified in `WFM/Agent_WFM.md` (prompts in `WFM/prompts/`):

   - **Agent 1:** Single LLM call: **flag** completeness and ambiguity (coreference under ambiguity), then **joint resolve** (most likely interpretation and guesses). **Plain NL output only** through Agent 2 — **no required metadata** for those steps.
   - **Agent 2:** Decomposition with a **compound-operator limit** (default **8**, `compound_operator_limit` in `WFM/config/wfm.json`); exceeding the limit **returns to user input** with an **Agent 2 error report** (structured trace per `WFM/prompts/agent_2_decomposition.md`) and message.
   - **Agent 3:** Scope check; **scope report** if no rewrite can be suggested (flow continues to Agent 4); **diff report** if a rewrite is proposed; if an **attempted rewrite fails** validation/policy, **return to user input** per WFM.
   - **Agent 4:** **Always** presents the confirmation package (decomposed text plus scope/diff material). User **yes** → continue to registry agent. User **no** → Agent 4 clarification/tentative-rewrite loop with fixed budgets; **inner** or **outer** exhaustion **returns to user input** with a **failure reason**. Re-runs of full WFM from agreed text follow `WFM/Agent_WFM.md`.

   WFM **always** presents cleaned output for **user confirmation** before passing to the registry agent. Scope and rewrite information is **always** included in Agent 4’s presentation when applicable.

   **WFM failure** (limits, exhaustion, or defined hard failures): pipeline **resets to the user input step** with an **explicit error message**; no registry/formalizer work proceeds until the user provides new input *(exact failure API/event shape is an open integration detail — see WFM “Open issues”).*

3. **Registry agent (LLM)** — multi-step workflow:
   - **Search first:** generate search terms from **WFM-cleaned, user-confirmed** statement, query registry via semantic search (embeddings). If registry is empty, skip search — everything is new.
   - **Extract gaps:** extract entities, types, functions, arities, constants from the cleaned statement, but only for things *not already covered* by search results. Registry search results are authoritative — extraction never overrides or contradicts existing registry entries.
   - **Resolve:** default is auto-confirm. Rewrite the original cleaned statement with matched registry entries substituted in (showing IDs and canonical names), and present side-by-side with the pre-resolved statement so user can scan and confirm at a glance. Only interrupt the user with an explicit choice when multiple competing matches exist (e.g., "did you mean the weight of the package or the weight of the item?"). The agent may also ask the user clarifying questions for any other reason it deems necessary — all questions must be phrased in plain language or project domain terms, never in programming or logic terminology. Both pre-resolved and resolved statements are stored for traceability.
   - **Populate:** after resolution (auto-confirmed or user-corrected), add new entries to registry and link existing entries. Return all relevant registry context for the formalizer.

4. **Formalizer (LLM)** — receives: WFM-cleaned statement + registry context (all relevant sorts, functions, constants with exact names and signatures) + instructions to produce Z3 Python code using only declared registry vocabulary.

5. **Z3 syntax/type check** — Z3 catches malformed code, type mismatches, undeclared identifiers for free.

6. **Identifier verification (fuzzy match + critic LLM)** — extracts identifiers from Z3 output, fuzzy-matches against registry ground truth, critic LLM flags suspicious mismatches (misspellings, invented names, conflated identifiers).

7. **Repair loop** — if errors at step 5 or 6, concatenate all errors into a single message: Z3 errors as raw exception strings + critic flags formatted as "Registry has 'X' but Z3 code used 'Y'". Send back to formalizer with the original Z3 code for repair. Budget: 1–5 iterations.

8. **Rule accepted** — Z3 assertion added to rule set. Cleaned English + Z3 code + rule ID + registry references saved to rules store.

---

## Registry Design

### Infrastructure:
- **Embedding model:** `BAAI/bge-base-en-v1.5` (local, no API cost)
- **Search index:** FAISS
- **Persistence:** JSON files on disk (`registry.json`, `rules.json`). Load on startup, save after each accepted rule.

### What the registry stores per entry:

- **ID** — unique, system-generated, immutable (e.g., `ent_001`, `fn_012`, `sort_003`)
- **Kind** — one of: `sort`, `constant`, `function` (predicates are functions returning Bool — no separate kind needed)
- **Name** — human-readable canonical name (e.g., `order_status`, `Biome`, `is_overdue`)
- **Signature** (functions only) — input sort(s) → output sort, arity
- **Parent sort** (constants only) — which sort this constant belongs to (e.g., `spring` belongs to `Season`)
- **Members** (sorts only) — list of declared constants in this sort
- **Source rule** — which rule(s) introduced or reference this entry
- **NL description** — short natural language description of what this entity/function means (e.g., "the biome where an animal naturally lives, such as forest or desert")
- **Embedding** — vector embedding of (NL description + canonical name), used for semantic search at step 3

### What to embed vs. keep exact:

- **Embed:** NL description + canonical name together as a single string. This is what semantic search queries match against. The description carries the meaning; the name carries lexical similarity.
- **Keep exact (never fuzzy-match):** ID, kind, signature, arity, parent sort, members. These are structural facts — either they match or they don't. The critic at step 6 uses these for verification.

### Why this split:

The formalizer LLM will sometimes say "animal habitat" when the registry has "habitat_biome." Embedding the NL description means the retrieval step finds it anyway. But the *output* Z3 code must use the exact canonical name and correct arity — that's what the identifier verification step checks.

---

## Consistency Checking — Deferred

Post-pipeline component. Will be designed after the core pipeline is built and tested.

---

## Canonical WFM reference

All WFM control flow, retry budgets, failure handling, loop-back rules, and open WFM issues are maintained in **`WFM/Agent_WFM.md`**. Agent instruction text is in **`WFM/prompts/`**.
