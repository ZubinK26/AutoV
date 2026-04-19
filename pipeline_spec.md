# NL→Z3 Formalization Pipeline — Scope & Architecture

This document describes the end-to-end pipeline. **Well-formedness (WFM)** behavior is defined in **`WFM/Agent_WFM.md`**; where details differ, **`WFM/Agent_WFM.md` takes precedence.**

**WFM config (defaults):** `WFM/config/wfm.json` — e.g. `max_input_code_points` (**4096** by default; see `WFM/Agent_WFM.md` for rationale).

**WFM LLM prompts:** `WFM/prompts/` (per-agent instruction files; see `WFM/prompts/README.md`).

**ASCII diagram (flow + what is built in repo):** [`pipeline_diagram.md`](pipeline_diagram.md)

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
2. **Registry agent** (search → extract gaps → resolve → populate; **Phase 1:** automated resolve per **`development_plan_registry_stage_v1.md`** — *Automated LLM resolution*)
3. **Formalizer**
4. **Identifier critic**

**LLM backends:** WFM and later pipeline stages are **model-agnostic**: you can use **Anthropic (Claude)**, **Google (Gemini)**, or **other** chat-completion APIs that your orchestration layer supports. **Gemini** is in active use for WFM smoke runs (e.g. `test_sets/scripts/run_wfm_folio_gemini.py`); Claude remains supported (e.g. `run_wfm_folio_claude.py`). The same prompt files under `WFM/prompts/` apply regardless of provider unless you introduce provider-specific variants.

### Steps:

1. **User input** — natural language rule, unrestricted phrasing. **Safety:** before WFM, enforce **`max_input_code_points`** from `WFM/config/wfm.json` (default **4096** Unicode code points). If over limit, return to input with counts vs. limit; no auto-chunking. See `WFM/Agent_WFM.md`.

2. **Well-formedness module (WFM)** — Runs **Agent 1 → Agent 2 → Agent 3**, then a **confirmation step** and **conditionally Agent 4 (LLM)**, as specified in `WFM/Agent_WFM.md` (prompts in `WFM/prompts/`):

   - **Agent 1:** Single LLM call: **flag** completeness and ambiguity (coreference under ambiguity), then **joint resolve** (most likely interpretation and guesses). **Plain NL output only** through Agent 2 — **no required metadata** for those steps.
   - **Agent 2:** Decomposition with a **compound-operator limit** (default **8**, `compound_operator_limit` in `WFM/config/wfm.json`); exceeding the limit **returns to user input** with an **Agent 2 error report** (structured trace per `WFM/prompts/agent_2_decomposition.md`) and message.
   - **Agent 3:** Scope check; **scope report** if no rewrite can be suggested (flow continues); **diff report** if a rewrite is proposed; if an **attempted rewrite fails** validation/policy, **return to user input** per WFM.
   - **Confirmation (product UI / templates):** The application **always** shows the **confirmation package** after Agent 3: decomposed sub-statements plus scope/diff material. User **acceptance** proceeds to the registry stage; reaching agreement may be handled by **orchestration alone** without an LLM (**yes** path). Per-line disagreement, **OUT_OF_SCOPE** handling, **`WFM_PATCH`** merge, and re-entry to WFM are specified in **`WFM/Agent_WFM.md`** (confirmation package, Agent 4, patch merge sections).
   - **Agent 4 (LLM):** **Not** used to render the initial static package. It is invoked **from the user’s response onward**, **typically when the user rejects** the package and supplies feedback—clarification, **`WFM_PATCH`** proposals (`replacements` only from the model; omissions from UI), and merge under `WFM/Agent_WFM.md`. **Inner** or **outer** exhaustion **returns to user input** with a **failure reason**. User-confirmed **merged natural language** (Style A join) **re-runs full WFM from Agent 1** per `WFM/Agent_WFM.md`. *(Repo test harness: Agent 4 drivers and **Style A** loop-back to Agents 1–3 live under **`test_sets/scripts/`** — see **`test_sets/README.md`**.)*

   WFM **always** offers **user confirmation** of cleaned output before passing to the registry agent. Scope and rewrite information is **always** included in that confirmation package when applicable.

   **WFM failure** (limits, exhaustion, or defined hard failures): pipeline **resets to the user input step** with an **explicit error message**; no registry/formalizer work proceeds until the user provides new input *(exact failure API/event shape is an open integration detail — see WFM “Open issues”).*

### WFM → registry handoff (orchestration payload)

After **user acceptance** of the confirmation package (per **`WFM/Agent_WFM.md`**: merged Style A text, PASS / REWRITE / OUT_OF_SCOPE as displayed), orchestration passes a **structured** payload to the registry stage—not NL alone—so the registry agent never has to re-infer line verdicts from prose.

**Rule granularity (resolved):** Each **accepted sub-statement** (one numbered line in the authoritative confirmation list) becomes **one formal rule** with its **own immutable `rule_id`** when the rule is later persisted after formalization. All lines accepted in a **single user acceptance** share a **`bundle_id`** (also **`wfm_acceptance_id`**). Preserve **`line_index`** (order within the bundle; 0-based or 1-based—pick one convention in implementation and keep it stable).

**Bundle-level fields (once per acceptance):**

| Field | Purpose |
|-------|--------|
| `bundle_id` | Stable id for this acceptance event. |
| `user_original_input` | Raw user submission (audit). |
| `confirmation_package_style_a` | Full joined NL the user saw (optional convenience for logging / whole-text search terms). |
| `orchestration_run_id` | Id tying this run to logs (implementation-defined). |
| `wfm_pipeline_timestamps` | e.g. confirmation accepted at (UTC); **include for audit**. |
| `provider_model` | Optional: WFM LLM provider + model id used (audit / regression). |
| `wfm_compound_operator_limit` | Value from `WFM/config/wfm.json` at run time (optional parity with harness). |

**Per-line fields (one object per line in the confirmation package):**

| Field | Purpose |
|-------|--------|
| `line_index` | Order within bundle. |
| `statement_nl` | Canonical WFM-cleaned NL for **this line only** — **input to the registry stage** (**search**, **gap extraction**, start of **resolve**). It is **not** the sole English input to the **formalizer**; after resolve, the formalizer uses **`registry_resolved_nl`** (see step 4). |
| `agent3_verdict` | `PASS` \| `REWRITE` \| `OUT_OF_SCOPE` (as shown post–merge). |
| `scope_report` \| `diff_report` | Present when applicable; `null` if not. |
| `agent2_line_text` | Pre–Agent 3 decomposition line for traceability (**recommended**). |

**OUT_OF_SCOPE lines:** Remain in the handoff with verdict **`OUT_OF_SCOPE`** and reports as applicable. Orchestration/registry policy: **skip formalization** (no Z3) for those lines; do not drop them from the payload so audit and future tooling stay complete.

**ID policy (resolved):** Registry entry **IDs** and rule **IDs** are **immutable**; no silent reuse (tombstone or equivalent if entries are retired)—see **Graph-friendly shape** below.

3. **Registry agent (LLM)** — multi-step workflow:

   **Phase 1 (registry stage v1 — `development_plan_registry_stage_v1.md` M3–M5):** **automated resolve only**. A structured LLM emits **`registry_resolution_candidate_nl`** and related fields; **programmatic validation** commits to **`registry_resolved_nl`** or **fails the line** with structured reasons — see **Automated LLM resolution** in **`development_plan_registry_stage_v1.md`**. There is **no** interactive disambiguation or registry review UI in this phase.

   **Full product (future):** optional **user** confirmation, structured choice among competing matches, and correction loops; background notes: **`archive/registry_resolution_interactive_design/`**.

   - **Search first:** generate search terms from **`statement_nl`** for each line (and optionally bundle-level `confirmation_package_style_a`), query registry via semantic search (embeddings). If registry is empty, skip search — everything is new.
   - **Extract gaps:** extract entities, types, functions, arities, constants from **`statement_nl`** for that line, but only for things *not already covered* by search results. Registry search results are authoritative — extraction never overrides or contradicts existing registry entries.
   - **Resolve:** rewrite **`statement_nl`** with matched registry entries substituted in (canonical names / ids). The result that **proceeds to populate and (later) the formalizer** is **`registry_resolved_nl`** (may equal **`statement_nl`** when no substitution was required). In Phase 1, **`registry_resolved_nl`** is set only after **automated validation passes**. In the full product, additional **user** approval may be required by policy before that write. **`pre_resolved_nl`** and **`registry_resolved_nl`** MUST be retained for traceability **per line** (keyed by `line_index` / `bundle_id`) and MUST be carried into the **persisted rule row** and any **per-line trace** (see **`registry_persistence_v1.md`**).
   - **Populate:** after a line **successfully** completes resolve (**`registry_resolved_nl`** set for that line), add new entries to registry and link existing entries. Return all relevant registry context for the formalizer **per in-scope line** (or once per bundle if implementation batches—context must remain attributable to each `rule_id` / `line_index`).

4. **Formalizer (LLM)** — receives: **per-rule** **`registry_resolved_nl`** (the registry-aligned English sentence **after** step 3 resolve — canonical registry names / substitutions; **Phase 1:** written by programmatic commit after automated resolve; **full product:** may also be user-approved) **plus** registry context (all relevant sorts, functions, constants with exact names and signatures) + instructions to produce Z3 Python code using only declared registry vocabulary. **Do not** formalize from **`statement_nl` alone** when it disagrees with **`registry_resolved_nl`** — doing so would mismatch vocabulary and accepted alignments. **`statement_nl`** remains on the rule for **audit** (WFM lineage). **Skip** lines with `agent3_verdict: OUT_OF_SCOPE` (no formal unit). Lines in the same **`bundle_id`** share the same populated registry vocabulary for that acceptance.

5. **Z3 syntax/type check** — Z3 catches malformed code, type mismatches, undeclared identifiers for free.

6. **Identifier verification (fuzzy match + critic LLM)** — extracts identifiers from Z3 output, fuzzy-matches against registry ground truth, critic LLM flags suspicious mismatches (misspellings, invented names, conflated identifiers).

7. **Repair loop** — if errors at step 5 or 6, concatenate all errors into a single message: Z3 errors as raw exception strings + critic flags formatted as "Registry has 'X' but Z3 code used 'Y'". Send back to formalizer with the original Z3 code for repair, still grounded in **`registry_resolved_nl`** + registry context (the English line does not revert to **`statement_nl`** unless the user re-runs resolve). Budget: 1–5 iterations.

8. **Rule accepted** — For each in-scope line in the bundle that passes Z3 + critic: Z3 assertion added to rule set. Per line: **`statement_nl`** (WFM lineage / audit) + **`registry_resolved_nl`** (English the formalizer used; registry-aligned) + Z3 code + **unique `rule_id`** + **`bundle_id`** + **`line_index`** + explicit **committed** **rule → registry entry** links (**labeled** by relationship kind; see **Graph-friendly shape**) saved to **`rules.json`** or an adjacent store. **Draft** links may exist only during steps 3–7 for operator/debug use; **default product queries and future contradiction tooling use committed links only.** **OUT_OF_SCOPE** lines do not receive a formal rule row unless product policy adds placeholder rows—default is omit from formal rule set only.

### Pipeline diagram (ASCII)

The text diagram and build-status legend are in **`pipeline_diagram.md`** (repo root, next to this file).

---

## Registry Design

**Resolved design choices (#1–#7)** for IDs, handoff, graph edges, rules↔registry alignment, and failure/commit are specified in subsections below (**Graph-friendly shape**, **Rules store ↔ registry alignment**, **Failure / commit contract**) and summarized in **`Registry_Way_Forward.ipynb`**.

**Implementation contract (v1 JSON keys, enums, Phase 1 pre–formalizer scope, gap / deferral table):** **`registry_persistence_v1.md`** (§§9–10).

**Development plan (milestones M0–M6 — registry stage before formalizer):** **`development_plan_registry_stage_v1.md`** (includes **Phase 1 automated LLM resolution** spec as a dedicated section). **Future** interactive resolve (not Phase 1): **`archive/registry_resolution_interactive_design/README.md`**.

### Infrastructure:
- **Embedding model:** `BAAI/bge-base-en-v1.5` (local, no API cost)
- **Search index:** FAISS
- **Persistence:** JSON files on disk: **`registry.json`**, **`rules.json`**, **`bundles/{bundle_id}.json`** (handoff), **`bundles/{bundle_id}.pipeline.json`** (orchestration status). Load on startup; **production** writes occur on **user-approved commit** (full or partial bundle)—see *Failure / commit contract (resolved)*.

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

### Graph-friendly shape (future contradiction / rule interactions)

**Consistency checking is deferred**, but the registry should remain **easy to traverse** once those features exist.

#### Resolved: graph edge model

The following is **decided** (see also **`registry_graph_edges_when_built_concrete.md`** for behavior in plain language; **`registry_graph_edges_design_choices.md`** for option trade-offs).

| Axis | Choice | Behavior |
|------|--------|----------|
| **Lifecycle** | **A3 — Draft + committed** | During registry populate → formalize → Z3 → critic, the pipeline **may** record **draft** **rule → entry** links for debugging. **Committed** links are written only when the rule is **accepted** (successful validation / defined commit point). **Default** tooling and contradiction prep **query committed links only**; draft must not appear as “official” graph state. |
| **Rule ↔ entry link shape** | **B3 — Labeled edges** | Persist **rule → entry** links as individual rows (or equivalent): **`rule_id`**, **`entry_id`**, **`relationship`** (closed enum defined at implementation—e.g. appears-in-FOL, mentioned-in-NL, created-by-rule, loaded-for-validation). Labels are derived from **pipeline artifacts** (NL token/linking, FOL AST walk, registry writes, Z3-facing theory), **not** from an LLM classifying arbitrary relations over the whole registry. |
| **Source rule vs rule-side index** | **C1 — Entry authoritative + mirrored index** | Each registry entry that “belongs” to a rule carries **authoritative** **`source_rule`** (or equivalent), supporting **multiple** rule IDs when an entry is reused. The rule record also holds **outgoing link rows** for fast **rule → entries** navigation; **update both in the same commit** so they do not drift. If the mirror diverges, **rebuild** the rule-side links from entries filtered by `source_rule`. |
| **Entry ↔ entry** | **D3 — Hybrid** | Store **entry ↔ entry** edges only where they are **non-trivial** or **hot** for structural search (e.g. schematic instance, explicit import). Relations **fully determined** by fields on the entries (e.g. constant → parent sort) **may be computed** when queried instead of duplicated in an edge table. |

**OUT_OF_SCOPE lines:** No formal rule row and **no committed** rule→entry spine for that line; they remain in the **handoff payload** only (see *WFM → registry handoff*).

Supporting points (unchanged intent):

- **Stable IDs:** Treat registry entry `ID` and rule `ID` as **immutable edge endpoints**; never recycle an ID after deletion (or maintain a tombstone) so historical edges remain interpretable.
- **Rule atoms:** Multiple **rule** rows may share one **`bundle_id`** (one user acceptance); graph and contradiction tooling may treat the bundle as a hyperedge or query by shared bundle for related assertions.
- **Separate index from graph:** FAISS (or any embedding index) answers *semantic neighborhood*; **contradiction-style search** will also need **structural** hops (shared predicate, overlapping constants). Keeping **structured fields** (`kind`, `signature`, `parent sort`, `members`) addressable without re-parsing JSON strings avoids painting us into a corner.

### Rules store ↔ registry alignment (resolved)

Persistence remains **`registry.json` + `rules.json`** (or equivalent). Background in plain language: **`rules_store_registry_alignment_explained.md`**.

| Topic | Resolution |
|-------|------------|
| **Where committed rule→entry links live** | **Canonical:** labeled **`committed_edges`** (or equivalent) **on each accepted rule record**. **No** second writable global edge store at v1. If scale requires a **derived** “all edges” export (e.g. JSON Lines), generate it **only** from rule records on save. |
| **Each rule row** | **Include:** `rule_id`, `bundle_id`, `line_index`, **`statement_nl`** (WFM-canonical; registry **input** lineage), **`registry_resolved_nl`** (post–step 3; **formalizer** English; MUST NOT be dropped — see steps 3–4), accepted formal artifact (Z3/code or stable pointer if large), **`committed_edges`** `[{ entry_id, relationship }]`. **Include for audit / log correlation:** **`wfm_pipeline_timestamps`** (or rule-accepted time) and **`orchestration_run_id`** — these are **already specified** in *WFM → registry handoff*; carry them into persisted rules when orchestration exists. **Do not** put **`handoff_ref`** on each rule row: the archived handoff path is **fully determined** by **`bundle_id`** (see below). |
| **Flat reference list** | **None.** Committed links are **labeled only** (matches **Graph-friendly shape**). |
| **Reuse and `source_rule`** | **`CREATED_BY_RULE`** (name at implementation) only when the entry is **introduced** for this rule on this commit. Reuse uses other labels (**appears-in-FOL**, etc.). **`source_rule`** on an entry lists **every rule** that has a **committed** link involving that entry (membership policy). |
| **Bundle record** | **Lightweight** record per **`bundle_id`:** ordered **`rule_id`**s, acceptance timestamp, optional **`orchestration_run_id`**. (Full handoff path follows convention; no **`handoff_ref`** field required.) |
| **Where the full WFM handoff lives** | The **registry** holds **dictionary entries** (symbols, descriptions, embeddings)—**not** the full structured handoff (raw user input, per-line Agent 2/3 reports, etc.). **Archive the full structured payload once per bundle** at **`bundles/{bundle_id}.json`**, alongside **`registry.json`** and **`rules.json`** under the same persistence root. **Convention only:** given **`bundle_id`**, tools load **`bundles/{bundle_id}.json`**—no per-rule pointer. A per-bundle **`handoff_ref`** override is **reserved** only for future irregular storage (migration, external object store), not the default product shape. |
| **Embeddings on rules** | **Deferred** until **contradiction / candidate-search** work. **Registry entry** embeddings + structural graph suffice for the core pipeline; add a **rule**-level embedding index when implementing semantic **rule** neighborhood search for contradiction **candidate** generation (same milestone, not a separate pre-contradiction project). |
| **Drift between rule edges and registry** | **Not** something end users repair. **Normal:** run a **`validate_alignment`** check (or CI): every **committed** edge implies **`rule_id ∈ entry.source_rule`**, and agreed bidirectional checks. **If validation fails:** treat as **bug or corrupted files**—restore from **backup** (standard ops), or **engineers** re-derive or re-run from **archived handoff** + pipeline; **trusted** state means “last known-good **committed** `rules.json` + `registry.json`” (formal code plus **`registry_resolved_nl`** / **`statement_nl`** as persisted), not a separate mystery artifact. |

### Failure / commit contract (resolved)

Orchestration persists **production** state alongside **`registry.json`** / **`rules.json`**. Aligns with *Graph-friendly shape* (draft vs committed) and *Rules store ↔ registry alignment*.

| Topic | Resolution |
|-------|------------|
| **Late durable registry** | **Production** `registry.json` is updated **only** when committing rules (**full** or **user-approved partial**), **not** immediately after populate alone. Tentative registry work during steps 3–7 is **in-memory** until that commit. |
| **Draft vs production (v1)** | Draft rule→entry links and tentative registry edits stay **in process memory** during the run—**no** separate persisted draft tree under `runs/` in v1 (keeps failure modes simple). **Crash / resume:** re-run the pipeline from **`bundles/{bundle_id}.json`** and the current **`bundles/{bundle_id}.pipeline.json`**. Add optional on-disk draft later only if **resume** becomes a hard requirement. |
| **Handoff and pipeline sidecar** | On **user acceptance**, write **`bundles/{bundle_id}.json`** (immutable handoff snapshot). **Mutable** pipeline state: **`bundles/{bundle_id}.pipeline.json`** with **`pipeline_status`** ∈ `pending` \| `committed` \| `partially_committed` \| `failed`; **`orchestration_run_id`**; **`updated_at`**; **`committed_rule_ids`** / **`committed_line_indices`** when **partial**; optional **`failure_summary`**. |
| **User-directed partial commit** | If some in-scope lines fail after repair: **no** automatic production write. Present per-line outcome; user may **abandon**, **commit all successes** (**full** if all passed, or **partial** if only a subset is committed), or **fix and re-run**. Each production commit is **one atomic write** of the chosen rule rows + registry deltas + **`committed_edges`** + bundle bookkeeping + updated **`bundles/{bundle_id}.pipeline.json`**. |
| **Retry of uncommitted lines** | Use a **new `bundle_id`** (new acceptance / new **`bundles/{bundle_new}.json`**) for lines that did not ship from the earlier bundle. Keeps audit linear; the earlier bundle remains **`partially_committed`** (or **`failed`** if user abandoned) with its handoff unchanged. |
| **Concurrency** | **Single writer** to `registry.json`, `rules.json`, and **`bundles/`** in v1. |
| **Idempotency** | **`bundle_id`** + **`orchestration_run_id`** (and **`pipeline_status`**) ensure a commit is not applied twice after retries. |
| **Recovery** | **Corruption:** restore from **backup**. **Logical** errors: **forward** supersede / new material; **no** silent history rewrite. **Admin “uncommit” / revoke:** **deferred** until a concrete ops need. |

### Phase 2 automation mode (extended e2e / no human-in-the-loop for steps 4–8)

Elsewhere this document describes **production** persistence using phrases such as **user-approved commit**, **user-approved partial**, **user-directed partial commit**, and “present per-line outcome” for a **human** to abandon / commit a subset / fix and re-run. Those phrases describe the **full interactive product**. A separate **automation mode** applies to the **Phase 2** implementation path that **extends the existing WFM → registry e2e** through formalization and commit **without** inserting approval dialogs between steps **4** and **8**:

| Spec language (interactive product) | Automation mode (default for extended e2e) |
|--------------------------------------|---------------------------------------------|
| **user-approved commit**; **Late durable registry** (“only when committing rules … **user-approved partial**”) | **Automatic commit** to `rules.json` / `registry.json` when **programmatic success** criteria are met for the run (per-line pass through steps 4–7; atomic write per policy). **No** separate human approval step before durable write. |
| **User-directed partial commit** (abandon / commit successes / re-run) | Implemented as a **fixed automation policy** (e.g. commit all lines that passed; fail bundle with no partial write; or commit partial successes — **TBD in dev plan**) **without** interactive prompts in the default loop. |
| Step **4** “**full product:** may also be **user-approved**” for **`registry_resolved_nl`** | **No** extra approval before formalization after **M4** validation has committed **`registry_resolved_nl`** for the line. |

**Inspection:** Operators **review** formalization output, Z3/critic results, and final persisted state via **artifacts, exports, and viewers** (view-only). That is **not** a gating “approval” step.

**Compatibility with bundle, entity, and structural navigation (Phase 2 does not require a prior “contradiction milestone”):** The **Rules store ↔ registry alignment** and **Graph-friendly shape** tables above already imply:

- **Filter rules by `bundle_id`:** Each accepted rule row carries **`bundle_id`**; bundle records list **`rule_id`**s — sufficient to list or index all rules for a bundle.
- **Rules involving a given registry entity (`entry_id`):** **`committed_edges`** on each rule reference **`entry_id`**s; registry entries carry **`source_rule`** listing **rule IDs** with **committed** links to that entry — sufficient for **entity-centric** rule lookup (reverse index from entry to rules, or scan rules).
- **One-hop structural hops:** **Rule → entries:** **`committed_edges`** on the rule row. **Entry → rules:** **`source_rule`** on the entry (and/or scan **`committed_edges`**). Deeper or **semantic** rule–rule search (e.g. embeddings on rules) stays **deferred** per *Embeddings on rules* above.

### Phase 2 — `committed_edges` extraction (contradiction-ready, single delivery)

**Product intent:** Do **not** split “early Phase 2” vs “late Phase 2” for graph edges. **`committed_edges`** (closed **`relationship`** enum in **`registry_persistence_v1.md`** §2) must be populated to the **satisfaction of future contradiction / structural search** (rule↔entry, **`source_rule`** mirroring) in the **same** Phase 2 program that ships formalization through production commit — **no** separate follow-up project to “fix” edges.

**Extraction approach (agreed):**

1. **Structured output from the formalizer** (step 4): besides **`z3_python_source`**, emit a **machine-validated manifest** of **`entry_id`** references and proposed **`relationship`** labels drawn only from the **closed enum** — with the same style of checks as registry resolve (**every `entry_id` ∈ session**, no invented IDs).
2. **Deterministic verification:** After step 5, **cross-check** (e.g. AST / identifier pass over the **accepted** formal artifact, and/or symbol reconciliation) so **`APPEARS_IN_FOL`** / **`LOADED_FOR_VALIDATION`**-style labels are **grounded** in the actual theory fragment, not LLM-only claims. **Pipeline-derived** edges take precedence over informal prose.
3. **Persistence:** **`committed_edges`** on each rule row and **`source_rule`** on entries are written at the **production commit** point (step 8 in the full pipeline); steps 4–5 **produce** the validated manifest + traces that commit logic **consumes** without reinterpretation.

**Normative reference:** **`registry_persistence_v1.md`** §2 (`relationship` enum), *Rules store ↔ registry alignment*, *Graph-friendly shape*.

### Phase 2 — executing formalizer output (step 5, safety without weakening goals)

Step 5 **runs** the generated Python that uses **`z3`** so malformed theories fail **with real Z3/Python errors** (feeding the repair loop). **Operational constraints** (subprocess, **timeout**, **import whitelist** — typically **`z3` only**, no network) **do not** relax formalization requirements: **`registry_resolved_nl`** grounding, declared vocabulary, critic, and repair semantics stay as in steps 4–7.

---

## Consistency Checking — Deferred

Post-pipeline component (may use **graph-style** traversal over rules + registry references as well as embedding search). Will be designed after the core pipeline is built and tested; see **Graph-friendly shape** above so early persistence choices do not block that.

---

## Canonical WFM reference

All WFM control flow, retry budgets, failure handling, loop-back rules, and open WFM issues are maintained in **`WFM/Agent_WFM.md`**. Agent instruction text is in **`WFM/prompts/`**.
