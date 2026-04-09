# Registry resolution (M4+) — open design issues

> **Archived (2026-04-04):** Not Phase 1. **Active spec:** repo root **`development_plan_registry_stage_v1.md`** (*Automated LLM resolution*). Stub: **`REGISTRY_AUTOMATED_RESOLUTION_PLAN.md`**. **`README.md`** in this folder.

**Purpose:** Capture design gaps and questions for **LLM-first resolve**, user involvement, retry/re-run loops, and guardrails—so discussion isn’t limited to chat. This is **not** a committed spec for Phase 1; historically it fed **`pipeline_spec.md`**, **`development_plan_registry_stage_v1.md`**, and **`registry_persistence_v1.md`**. For **interactive** workflow revival, merge or replace with a fresh doc that references this archive.

**Proposed direction (from product discussion):** Resolve primarily via a **resolution LLM** fed match results and supporting context; each pass emits **`registry_resolution_candidate_nl`** (substitutions + rephrase; may include **provisional** new-entity wording until identity is decided). Only after **commit** (**`AUTO_ACCEPTED`** / **`USER_ACCEPTED`** per **A.15**) is that line written as **`registry_resolved_nl`** for formalizer and persisted rule rows (**`pipeline_spec`**). **User involvement** is gated by policy + model signals, with recorded decision/justification. **Inner loop:** user comments → resolver with budget + prompt guardrails. **Outer loop:** when inventory/assumptions are invalid, **re-run the registry workflow from search** (or from a defined “step 1”) with its own budget—to mitigate cases like user correcting “Paul” → “Jeff” while “Jeffrey” already exists. Outcome classes include auto-accept, accept without/with comments (no full re-run), and worst-case re-run.

---

## Part A — Issue list (assessment text, from design review)

Use this list for threaded discussion; strike through or move to “Decided” when settled.

### A.1 Vocabulary: `statement_nl`, `pre_resolved_nl`, **`registry_resolution_candidate_nl`**, `registry_resolved_nl`

**Status:** **Decided** — **Tier T1a** **resolved** (supplemented with **candidate** vs **committed** resolved line — see below).

**Clarified (discussion):** Per **`pipeline_spec.md`** handoff table, **`statement_nl`** is *“Canonical WFM-cleaned NL for this line only — **input to the registry stage** (search, gap extraction, **start of** resolve).”* That is exactly the **WFM → registry boundary artifact** (after user acceptance of the confirmation package, before registry has finished rewriting). **No new name is required** for that meaning—**`statement_nl`** is the correct field.

**Align (agreed direction):** **`pre_resolved_nl` should stay equal to `statement_nl`** for that line/session unless you later introduce a *real* intermediate (a deliberate product choice to mutate the “left column” before acceptance). **Guardrails** (“stay close to WFM”) use **`statement_nl`** / **`pre_resolved_nl`** as the **left-column** anchor.

**`registry_resolution_candidate_nl` (new, required naming):** The **working proposal** from each resolver pass—validation retries, inner comment rounds, or first auto attempt. It is what the UI shows on the **right** against **`statement_nl`** / **`pre_resolved_nl`** while resolve is **in flight**. It may contain **undecided** or **provisional** registry wording (new entities not yet populated or named in session); anything **new** is treated as **provisional** until the resolution loop commits. **Do not** label this string **`registry_resolved_nl`** in traces or product language until commit.

**`registry_resolved_nl` (committed only):** Per **`pipeline_spec`**, the **user-approved** (or policy-**`AUTO_ACCEPTED`**) registry-aligned English used by the **formalizer** and persisted on the **accepted** rule row. It is **set or updated only** when resolve **commits**—not on every model turn. Promoted from the accepted **`registry_resolution_candidate_nl`** (same text or user-edited equivalent).

**Trace / persist:** For **`pipeline_spec`** traceability, retain **`pre_resolved_nl`** next to **`registry_resolved_nl`** on the **committed** handoff; per-attempt snapshots store **`registry_resolution_candidate_nl`** (**A.12**).

### A.2 LLM-only resolve vs hybrid paths

**Status:** **Decided** — **Tier T4a** **resolved**. Product accepts **LLM-only resolve** for **v1** (and as the working architecture until explicitly re-opened): every line’s **rewrite** is produced through the **resolution LLM** as **`registry_resolution_candidate_nl`**, then promoted to **`registry_resolved_nl`** only on commit (**A.1**), with structured output and programmatic validation (**A.4**). There is **no** parallel non-LLM “fast rewrite” branch in v1.

**Tradeoff accepted:** Single path simplifies engineering and matches **`pipeline_spec.md`** intent; cost/latency/variance are managed via **policy**, **A.3** auto-skip (presentation, not a second rewriter), monitoring, and eval—not by skipping the model for the rewrite step.

**Out of scope (until a future explicit decision):** **Hybrid** shortcuts (e.g. identity copy-through when zero gaps) would need their own design pass, **A.7** calibration, and regression tests; they are **not** part of the committed v1 design.

### A.3 “High confidence → skip user” is underspecified

**Status:** **Partially decided** — **Tier T2c**; **precedence**, **structure**, and **v1 prototype `AUTO_ACCEPTED` policy** frozen below. **Explicitly deferred (full closure):** top-2 margin **ε**, **`medium`** / banded auto rules, fuller “never auto if …” matrix—tune after **A.7** (**M3**) and **A.11** / **M5** where provisionals interact with tenant config.

**Recommended decision order (v1):** **(1)** Tenant / compliance / **`POLICY_REVIEW_REQUIRED`** overrides → **(2)** programmatic validation failure (guardrails, referential checks) → **(3)** **`needs_human_review`** from structured output → **(4)** **`confidence_tier`** and code-based auto bans (e.g. never auto-accept when `primary_review_reason` is in a configured blocklist). **`confidence_tier`** alone must not override hard policy.

**`AUTO_ACCEPTED` — v1 prototype (decided):** Allow **only** when **all** are true: **(a)** no active **`POLICY_REVIEW_REQUIRED`** for this line/bundle; **(b)** programmatic validation passes (including referential closure); **(c)** `needs_human_review == false`; **(d)** `primary_review_reason` is **`NONE`** (or equivalent); **(e)** `confidence_tier == high`; **(f)** structured output contains **no** provisional / new-entity markers requiring review (**A.11**). Otherwise use the review / present-user path. This avoids guessing **ε** and **medium**-tier auto until **A.7** eval.

**Still underspecified (post-prototype refinement):** exact ε, optional second check (rules vs mini-step), tenant-specific relaxations of (e)–(f). **A.4** supplies flags and reason enums—**A.3** combines them with policy as above.

### A.4 Taxonomy of “why involve the user”

**Status:** **Decided** — **Tier T1b** **resolved** (exact trace JSON in **A.12**; numeric thresholds remain to calibrate in eval).

**Codes (accepted):** **One primary** + optional **secondary** reason tags from the closed set below. **Single resolve API call** per attempt (unless validation retry or user-driven inner loop); model returns **structured fields**; **UI copy** is assembled **programmatically** from those fields plus thin templates—not a second LLM call for default UX.

**Recommendation:** Use a **small closed set** of **primary** reason codes (machine-usable enums). If two apply, store **one primary** + optional **secondary** tags so traces and UI don’t explode combinatorially.

| Code | Definition (when this is the *primary* driver) | Typical user-facing content |
|------|-----------------------------------------------|-----------------------------|
| **`MAPPING_AMBIGUOUS`** | For at least one span/gap role, **two or more registry entries** score above a relevance threshold and the resolver cannot pick a unique winner **without policy**. | Side-by-side of **candidate entries** (id, name, kind, one-line NL), optional similarity scores; user picks mapping or “none of these.” |
| **`NEW_VS_REUSE_UNCLEAR`** | Resolver thinks a gap needs a **registry symbol**, but it is **unclear** whether to **attach** an existing entry vs **plan a new** one (populate later). Distinct from pure ambiguity when one candidate is clearly “new concept.” | “Link to existing …” vs “Treat as new symbol (provisional)” with short **risk note**; may fuse with re-search suggestion. |
| **`NEAR_DUPLICATE_RISK`** | Proposed wording or target symbol is **string-/embedding-close** to an **existing** entry (Jeff vs Jeffrey, Acme vs ACME Corp). | Show **existing** entry(s) + “Did you mean this?” vs “No, distinct entity.” |
| **`INVENTORY_MISMATCH`** | User comment or model output introduces **entities or tokens** not justified by **current** search/hit/gap closure (your Jeff case after user correction). Often triggers **outer re-run** policy, not just another resolve pass. | Explain “we need to re-check the registry with updated text” or offer **forced re-search** path. |
| **`WFM_SCOPE_TENSION`** | Proposed **`registry_resolution_candidate_nl`** appears to **add/remove logical content** relative to **`statement_nl`**/WFM verdict (e.g. new quantifier, contrary to PASS scope). | Diff view + require explicit user ok or **reject** with comment. |
| **`POLICY_REVIEW_REQUIRED`** | **Product rule**: this bundle, tenant, or line class **always** shows the user (compliance, pilot mode). | Same UI shell; banner cites policy, not model doubt. |
| **`MODEL_REQUESTS_REVIEW`** | **Catch-all** when structured output sets `needs_human_review` but **no other code fits**—should be **rare** after good categories; use to avoid Silent failures. | Generic “please confirm” with model short rationale; tighten taxonomy over time so this fades. |

**Why these split the old blob:** “Many substitutions possible” → **`MAPPING_AMBIGUOUS`**. “Might need a new entity” → **`NEW_VS_REUSE_UNCLEAR`**. “Jeff vs Jeffrey” → **`NEAR_DUPLICATE_RISK`** (often found in resolve; root fix may be re-search → **`INVENTORY_MISMATCH`** if user changes facts).

**Confidence vs structure:** These codes classify **why** a case might deserve human attention; they are **not** automatic triggers. Situations such as **two plausible registry entries** or **new symbol vs reuse** are expected to be **resolved by the model when confidence is high**. Prompts (and schema) should carry **per-code guidance**—and, where useful, **per role / span**—on what lowers vs raises confidence (pattern similar in spirit to the **scope agent** spec). That scales coverage without exploding combinatorics, **provided** the guidance stays **structured** (short criteria + required fields), not a wall of prose per code. **Hard product gates** (e.g. **`POLICY_REVIEW_REQUIRED`**, compliance paths) **override** model self-confidence.

**Structured resolver output — minimum flags & UI slots (decided):**

| Field (conceptual) | Role |
|--------------------|------|
| **`registry_resolution_candidate_nl`** | Proposed line from this resolver pass (subject to validation); may be **provisional**; becomes **`registry_resolved_nl`** only on commit (**A.1**). |
| **`needs_human_review`** | Boolean; **policy** may force `true` regardless of model. |
| **`primary_review_reason`** | Enum from A.4 codes, or **`NONE`** / null when not asking user. |
| **`secondary_review_reasons`** | Optional small list (e.g. max **2**) of additional codes. |
| **`confidence_tier`** | e.g. **`high` / `medium` / `low`** (or numeric with mapped bands); feeds **A.3** caps—**not** trusted alone vs **POLICY_REVIEW_REQUIRED**. |
| **`llm_rationale_short`** | Short string for traces and optional UI “why.” |
| **`recommended_option_id`** | When choices exist: which option the model recommends. |
| **`options[]`** | Structured alternatives: **id**, **label**, **one_line_evidence** (and entry ids as needed)—feeds programmatic review UI. |

**Validation re-invoke budget (decided, realistic v1):** At most **2 automatic re-prompts** of the resolver **after** a **programmatically failed** attempt on the **same** line (wrong ids, guardrail fail, invalid JSON/schema parse after repair attempt, etc.) — i.e. **up to 3** model invocations in that **validation-retry** chain before escalating per policy (**present partial result**, **fail line**, or hand to user). **Not** the same counter as **user-comment rounds** (**K**) or **outer workflow re-runs** (**R**); see **A.9**.

**What triggers validation re-invoke (decision; not yet in `pipeline_spec.md`):** **`pipeline_spec.md`** does not yet spell out resolve-stage **automatic** retries; this list is the **working** trigger set to fold into the spec later: **schema/JSON invalid** (after optional single repair pass); **registry / session referential** checks (cited **`entry_id`**s or mapping keys not in allowed session closure); **guardrail failures** per **A.7** (edit distance vs **`statement_nl`**, WFM scope tension, disallowed vocabulary); **policy rejection** of an auto-only path (e.g. new symbol when tenant forbids auto). **Not** a separate trigger: model merely *suggesting* low confidence — that flows through **`needs_human_review`** in the **same** successful parse.

**Gap (remaining for A.12 / eval):** Numeric thresholds (scores, edit distance to existing names), **exact** persisted JSON field names and nesting, prompt-embedded criteria per primary code.

### A.5 What we show the user (content of the choice UI)

**Status:** **Decided** — **Tier T2a** resolved at product level. **Implementation:** layout, component copy, and i18n belong in **UI specs** (flagged for later wiring).

**Shell (from Tier 1):** Programmatic review UI fed by **`options[]`**, **`recommended_option_id`**, **`llm_rationale_short`**, **`primary_review_reason` / secondaries**, with **`statement_nl`** / **`pre_resolved_nl`** vs **`registry_resolution_candidate_nl`** as in **A.1**. Per-code **typical content** remains the A.4 table’s third column.

**Diff (left anchor vs proposed `registry_resolution_candidate_nl`):**

- **Mandatory** when **`WFM_SCOPE_TENSION`**, **`NEAR_DUPLICATE_RISK`**, or **`MAPPING_AMBIGUOUS`** is **primary or** among **secondary** reasons (user is being asked because mapping or meaning is sensitive). Omit diff only if there is **no** proposed rewrite to show (edge case).
- **Default** for other review-driving codes: show a **compact diff** (collapsed/expandable acceptable).
- **Optional / minimal** only for purely **structural** pick-one UIs where there is **no** NL rewrite yet.

**Free-text:**

- **Structured choice first.** Do **not** require a large comment box for a simple **accept as recommended**.
- **Optional short free-text** on **reject**, **“none of these,”** and when taking an **alternate** if audit needs rationale; single optional clarification when **`USER_ACCEPTED`** via **alternate structured choice** is acceptable v1.

**Gap (wiring only):** exact components, strings, and accessibility — **not** open design questions for **A.5**.

### A.6 Inner loop: comments → same resolver

**Status:** **Partially decided** — **Tier T3d**; **context shape and governance** for the comment loop are set below. **T1a–T2** already fix **K = 3** (**A.9**), structured choices + optional short text (**A.5**), and trace counters (**A.12**).

**Decided (v1 structure):**

- Each comment round sends the resolver a **bounded package**: current **`registry_resolution_candidate_nl`**, **frozen** mappings / span ids (locked user/model decisions), **open** span ids, and a **short rolling summary** of prior rounds — **not** unbounded raw chat.
- **Re-run from search** (outer loop, **`R`**) is **not** triggered by model whim alone; it is allowed only via **deterministic / policy** paths aligned with **A.10** (e.g. **`INVENTORY_MISMATCH`**, new token outside session closure, user explicitly chooses re-search) — see **M4**.

**Risks (unchanged):** **context explosion**, **goal drift** (“user said Jeff” without re-search) — mitigated by structure above + **A.10** / outer loop when inventory is stale.

**Completion gap (full Tier T3d closure):** **M4** — crisp rules when user input **stays in inner loop** vs **forces outer re-run** (and how that interacts with **K** exhaustion). Optional later: tighten per-round prompts once **A.7** numeric guardrails exist.

### A.7 Edit-distance / WFM guardrails

**Status:** **Partially decided** — **Tier T3a**; **layers and intent** frozen; **numeric thresholds** wait for eval (**M3**).

**Decided (v1 checklist — operationalize in code, calibrate numbers later):**

1. **Syntactic / surface proximity** to **`statement_nl`** (length, overlap, token edit distance) — **insufficient alone** for entity-swap cases (e.g. Paul→Jeff).
2. **Logical / WFM** consistency (no new quantifiers or operators beyond WFM scope for the line; aligns with **`WFM_SCOPE_TENSION`** / validation rejection).
3. **Registry / session referential** — cited ids and mappings must lie in **allowed session closure** (already tied to validation retries in **A.4**).
4. **Near-duplicate / inventory** signals — tie to **search or registry** and reason codes (**`NEAR_DUPLICATE_RISK`**, **`INVENTORY_MISMATCH`**), not only raw edit distance.

**Gap (unchanged by partial closure):** Concrete **ε**, margins, and automation-friendly tests — **A.3** auto-skip and guardrail enforcement depend on these.

**Completion gap (full Tier T3a closure):** Published thresholds + eval set; sync with **`pipeline_spec.md`** and validation retry copy in **A.4**.

### A.8 Jeff vs Jeffrey (example failure mode)

**Status:** **Partially decided** — **Tier T3c** (trace / continuity); **merge semantics** for session hits remain **M2**.

**Decided (v1 trace discipline):** **`line_index`** stays **stable** across outer passes; step **`outer_rerun_count`** / **`search_generation`** (or equivalent) with each **A.9** outer re-run; persist an **append-only** (or snapshot-per-generation) record of hit/gap state — **no silent overwrite** of prior audit. Aligns with **A.12** counters.

**Problem statement (unchanged):** The failure is **gap discovery + dereference**, not only bad rephrase. Re-running **from search** with updated user-approved text is the right class of fix **if** user corrections are **new evidence** requiring **re-embedding / re-retrieval**.

**Completion gap (full Tier T3c closure):** **M2** with **T3b** — **merge vs replace** of retrieval sets per line when an outer re-run (**`R`**) runs (**A.9** accounting **decided**).

### A.9 Three budgets (do not conflate)

**Status:** **Decided** — **Tier T2d** **resolved** for **v1** (numeric caps + **`R`** accounting). **M2** still refines **when** outer re-run is **mandatory** (trigger matrix) and retrieval **merge vs replace** (**A.8**)—not the meaning of **`R`**.

**`outer_rerun_count` / `R` (decided):** **`R`** increments **only** when a **full outer registry re-pass** runs (search / embed / hit refresh from the agreed workflow step)—i.e. **`OUTER_RERUN_TRIGGERED`** consumes **`R`**. **Inner** comment rounds (**K**), **validation retries**, and edits to **`registry_resolution_candidate_nl`** **without** that outer pass **do not** bump **`R`**. Inner token changes alone **do not** reset **`R`**; policy may still **schedule** an outer re-run (then **`R`** applies).

Registry resolve uses **three independent** limits:

| Budget | Meaning | **v1 value** |
|--------|---------|----------------|
| **(1) Validation retries** | Automatic **re-prompt** of the resolver after **programmatic rejection** of output (schema, ids, guardrails) on the **same** line—**no** user comment required. | **2** re-prompts after first failed attempt (**up to 3** model calls in that chain). See **A.4**. |
| **(2) Comment rounds (`K`)** | User-driven **inner loop:** structured feedback / alternate → **new** resolver invocation. Distinct from (1). | **`K = 3`** rounds; on exhaustion → **canned outcomes** (force pick among allowed ends, **fail line**, or policy path). |
| **(3) Outer re-runs (`R`)** | Full registry **workflow** re-pass from search (or agreed step 1)—inventory / embedding / hit set refresh. Distinct from (1) and (2). | **`R = 2`** per line/bundle policy (define in implementation); on exhaustion → **pause bundle**, **partial commit**, or **escalate** per policy. |

**Exhaustion:** Each budget should land in a defined **A.15**-friendly outcome (e.g. **`INNER_LOOP_EXHAUSTED`**, **`RESOLVE_FAILED`**, pause states)—canned outcomes with **M2** where coupled to outer triggers.

### A.10 “Resolution agent certifies re-run needed”

**Status:** **Partially decided** — **Tier T3b**; **governance principle** and **seed triggers** below; **full matrix + `R` accounting** = **M2**.

**Decided (v1):** The model may **emit a signal** that an outer re-run would help; **only deterministic rules + policy** may **commit** an **`R`**, set **`OUTER_RERUN_TRIGGERED`**, and re-embed / re-search. No **LLM-only** certification of inventory sufficiency.

**Seed list (non-exhaustive — refine with M2):** Outer re-run is appropriate when e.g. **`INVENTORY_MISMATCH`** / **`primary_review_reason`** path applies; **new surface token** not in current hit+gap closure; **structured user input** introduces a **name** not in session; user explicitly requests re-search; optional later: match-quality collapse after user-edited text (thresholds per **A.7**).

**Completion gap (full Tier T3b closure):** **M2** — authoritative **when-to-run-outer** trigger list aligned with **`R = 2`** (**A.9** accounting **decided**).

### A.11 Populate vs resolve boundary

**Status:** **Partially decided** — ties **M5** and populate tooling; **v1 vocabulary** below aligns with **A.1**.

**Decided (v1 semantics):** Anything **new** introduced in resolve exists first in **`registry_resolution_candidate_nl`** and is **provisional** until the loop commits: either the user/system **binds** it to an **existing** `entry_id`, **accepts** explicit provisional markers + populate path, or **re-runs** search / outer loop when inventory is wrong. **`registry_resolved_nl`** is **not** written for that line until there is a **committed** outcome (**`AUTO_ACCEPTED`** / **`USER_ACCEPTED`**)—so a looped-back sentence with undecided new entities never masquerades as “registry resolved” in the **`pipeline_spec`** sense.

**Structured output:** Resolver should mark provisional spans / new-symbol intent in schema (exact keys **A.12** / implementation) so validation and **A.3** auto policy can require review when provisionals are present.

**Completion gap:** Persistence of provisional placeholders vs **draft** registry rows; exact **AUTO_ACCEPTED** rules when provisionals exist (**M5** + **A.3**).

### A.12 Audit trail

**Status:** **Decided** — **Tier T2b** **resolved** at **v1 trace contract** (what must be persisted). **Deferred without blocking:** exact JSON **field names**, **nesting**, and **redaction** policy text—finalize in **`pipeline_spec.md`** / persistence doc / schema file when implemented.

**v1 skeleton (dimensions to record):**

- **`outcome_state`:** value from **A.15** when terminal or material snapshot when pending.
- **Reasons:** **`primary_review_reason`** + **`secondary_review_reasons`** (or normalized equivalent) aligned to **A.4**.
- **Resolver attempt snapshot:** at least **`registry_resolution_candidate_nl`**, **`needs_human_review`**, **`confidence_tier`**, **`recommended_option_id`**, **`options[]`** (or hash + store-once policy), **`llm_rationale_short`** on each material attempt.
- **Committed handoff (on `AUTO_ACCEPTED` / `USER_ACCEPTED`):** final **`registry_resolved_nl`** promoted from the accepted candidate (same text unless policy allows user edit); sub-fields per **A.15** (recommendation vs alternate + **option / mapping ids**).
- **Counters:** **`validation_retry_count`** (chain **A.4**), **`user_comment_round_index`** (≤ **K** from **A.9**), **`outer_rerun_count`** (≤ **R** from **A.9**).
- **Correlation:** **`bundle_id`**, **`line_index`**, session / attempt ids as required by **`registry_persistence_v1.md`**.

Legacy sketch (`resolution_path`, `review_required_reason[]`) maps to the above; prefer **A.15** + **A.4** enums as source of truth.

### A.13 Alignment with current written intent

`pipeline_spec` already says **Registry agent (LLM)** and **rewrite with substitution**; LLM-first resolve **fits** that spirit better than “string replace only.” **Gap in docs today:** sync **`pipeline_spec.md`** and persistence with **`registry_resolution_candidate_nl`** vs **`registry_resolved_nl`** (**A.1**), **A.2** (LLM-only resolve), **A.3**–**A.5**, **A.9** (three budgets), **A.12**, **A.14**, **A.15**; **guardrails** (**A.7**), **re-run merge** (**A.8**), and **populate boundary** (**A.11**) still refine control flow.

### A.14 Compliance hooks and concurrency (prototype v1)

**Status:** **Decided** — **Tier T5b** **resolved** for **v1 prototype**. **Post-prototype:** richer compliance taxonomies and multi-editor locking are out of scope here.

**What “the problem” is (plain language):**

1. **Compliance:** In some settings, certain lines or bundles **must** go to a human **even when the model is confident** (pilot mode, regulated content, tenant policy). The design risk is inventing a **second, ad-hoc** gate that fights **`A.3`** / **`A.4`**.  
2. **Concurrency:** While resolve runs, the **live registry** (or shared files) might **change**—another process edits entries, deletes an id your session still cites. The risk is committing **`registry_resolved_nl`** that looks valid inside the **session snapshot** but is **wrong relative to the live registry**, without anyone noticing.

**v1 prototype decisions (conservative defaults — full review and correctness paths preserved):**

| Topic | Decision |
|-------|----------|
| **Compliance** | **No separate mechanism.** Mandatory human review is expressed only through existing **`POLICY_REVIEW_REQUIRED`** (**A.4**) and **tenant / bundle config** read by the **A.3** precedence ladder (policy **before** model “auto-skip”). Prototype **must keep** that path **fully wired**: if config says “always show user,” **never** bypass the review UI. Optional: `compliance_mode: strict` on a bundle forces **`needs_human_review`** / blocks **`AUTO_ACCEPTED`** for configured line classes—implementation detail, same gates. |
| **Concurrency** | **Session snapshot is authoritative** for the lifetime of a resolve attempt: registry slice + search hits (and versions / hashes if available) **frozen** at **bundle session open** or at each **outer re-run** (**`R`**) boundary—aligned with **partial A.8** / **A.12** snapshots. **Do not** silently refresh mid–inner-loop from live registry. **If** the implementation detects **broken referential integrity** (cited `entry_id` missing or version mismatch): **fail validation** or **force user-visible path** (re-search / outer re-run)—**never** silent wrong commit. Single-operator prototype may rarely hit this; the rule still preserves correctness when it does. |
| **Scope honesty** | **v1** does **not** require legal-grade compliance matrices or distributed locks; it **does** require **hooks** above so nothing in the prototype **pretends** review or freshness that product policy forbids. |

**Completion gap (beyond prototype):** Legal sign-off catalog, multi-writer merge policies, live invalidation UX polish—**not** blocking v1 resolve behavior.

### A.15 Resolution outcome states (resolve machine vocabulary)

**Status:** **Decided** — product accepted the vocabulary below; **Tier T1c** is **resolved** (implementation details of audit JSON remain **A.12**).

**Purpose:** Shared **enum-like labels** for **where a line’s resolve attempt ended up** (or is waiting)—so **budgets (A.9)**, **audit (A.12)**, and tooling agree.

**Vocabulary:** Prefer **stable snake_case** (or SCREAMING_SNAKE) strings in traces; UI may map to human phrases.

| State | Meaning |
|-------|---------|
| **`RESOLVE_PENDING`** | Resolve not finished; no terminal outcome yet. |
| **`AUTO_ACCEPTED`** | Passed auto policy + model confidence; accepted **`registry_resolution_candidate_nl`** **promoted** to **`registry_resolved_nl`** (subject to **A.3** / **A.4** / provisionals — **A.11**). |
| **`PRESENTED_TO_USER`** | Choice UI shown; user has not yet confirmed (non-terminal for audit until accept/reject path completes). |
| **`USER_ACCEPTED`** | User confirmed a **`registry_resolution_candidate_nl`** (or equivalent choice); outcome **promotes** to committed **`registry_resolved_nl`** per **A.1**. |
| **`USER_REJECTED_OR_HELD`** | User refused / deferred (policy-specific); may feed inner loop or pause. |
| **`INNER_LOOP_EXHAUSTED`** | Inner comment rounds hit budget **K** without clean accept (**A.9**). |
| **`OUTER_RERUN_TRIGGERED`** | Full registry re-pass from search (or defined step 1) scheduled or in progress (**A.8**, **A.9**). |
| **`RESOLVE_FAILED`** | Hard failure for the line (policy: partial bundle, escalate, etc.). |

**`USER_ACCEPTED` audit sub-fields (decided):** Keep a **single** top-level outcome; record **how** the user accepted via sub-fields—e.g. **accepted as LLM recommendation** vs **accepted via alternate structured choice** (user selected a different option than the default recommendation). Store **option / mapping ids** as needed for traces. This replaces caring about “with comments” as a separate state when “comments” means **those structured choices**, not a distinct lifecycle state.

---

## Part B — Dependency order (work mindful of downstream)

Work **higher tiers before lower** so downstream issues don’t churn. Items in the **same tier** can proceed in parallel **unless** a mutual-dependence note says otherwise.

### Tier 1 — Foundation (blocks tracing, guardrails, and budgets)

| ID | Issue | Notes |
|----|--------|--------|
| **T1a** | **A.1** Vocabulary | **Resolved.** **`statement_nl`**, **`pre_resolved_nl`**, **`registry_resolution_candidate_nl`**, **`registry_resolved_nl`** — **A.1**. |
| **T1b** | **A.4** Taxonomy + structured resolve output | **Resolved.** Codes, primary/secondary tags, one-call + programmatic UI, flags table, validation retry (**2** re-prompts), trigger list — see **A.4**. |
| **T1c** | **A.15** Resolution outcome states | **Resolved.** Vocabulary decided in **A.15** (incl. **`USER_ACCEPTED`** sub-fields). Budgets (**A.9**) / audit (**A.12**) can assume these labels. |

*T1a and T1b are somewhat co-designed (categories may reference which NL baseline is shown). See mutual dependencies.*

### Tier 2 — Depends on Tier 1

| ID | Issue | Notes |
|----|--------|--------|
| **T2a** | **A.5** What we show the user | **Resolved.** Diff + free-text rules — **A.5**; UI spec wiring later. |
| **T2b** | **A.12** Audit trail fields | **Resolved** (v1 trace contract). Exact JSON keys / nesting / redaction deferred — **A.12**. |
| **T2c** | **A.3** Auto-skip user / confidence policy | **Partially resolved.** v1 **`AUTO_ACCEPTED`** predicate + precedence — **A.3**; **deferred:** ε, **medium** auto, full matrix (**A.7** / **M5**). |
| **T2d** | **A.9** Three budgets + **`R`** accounting | **Resolved.** Three caps + **`R`** only on outer re-pass — **A.9**. **M2:** when outer run is **required** + **A.8** merge. |

### Tier 3 — Depends on Tier 2 (and Tier 1 for baselines)

| ID | Issue | Notes |
|----|--------|--------|
| **T3a** | **A.7** Guardrails | **Partially resolved.** Layered checklist — **A.7**; **completion:** numeric thresholds, **M3** eval. |
| **T3b** | **A.10** Re-run certification / triggers | **Partially resolved.** Principle + seed list — **A.10**; **completion:** **M2** trigger matrix. |
| **T3c** | **A.8** Trace / outer generations | **Partially resolved.** Stable **`line_index`**, append-only snapshots — **A.8**; **completion:** merge vs replace **M2**. |
| **T3d** | **A.6** Inner comment loop | **Partially resolved.** Bounded context + no model-only outer jump — **A.6**; **completion:** **M4** (stay inner vs force re-run). |

### Tier 4 — Architecture choice (informed by Tier 1–3, not blocking vocabulary)

| ID | Issue | Notes |
|----|--------|--------|
| **T4a** | **A.2** LLM-only vs hybrid resolve | **Resolved.** **LLM-only** v1 — **A.2**. |

### Tier 5 — Boundary and ops (after core loop is stable)

| ID | Issue | Notes |
|----|--------|--------|
| **T5a** | **A.W** Populate vs resolve (**A.11**) | **`registry_resolution_candidate_nl`** / provisionals vs committed **`registry_resolved_nl`** — **A.11**; outcomes **A.15**; re-run **T3c**. |
| **T5b** | **A.14** Compliance + concurrency | **Resolved** (v1 prototype). Policy = **A.3** / **`POLICY_REVIEW_REQUIRED`**; snapshot + no silent live merge — **A.14**. |

---

## Part C — Mutual / recursive dependencies (handle together)

These pairs (or small sets) need **joint** decisions or tight iteration—not fully sequential.

| Set | Issues | Why simultaneous |
|-----|--------|------------------|
| **M1** | *(closed at design level)* | **A.5** resolved; any follow-up is **UI spec** implementation only. |
| **M2** | **T3b** + **T3c** ( + exhaustion UX) | **`R`** accounting fixed in **A.9**; **M2** couples **when** outer re-run **must** fire, hit-set **merge/replace** (**A.8**), and canned outcomes when **K** or **R** exhausts. |
| **M3** | **T3a** (guardrails) + **T1a** (baseline) | **T1a** resolved; **T3a** checklist decided in **A.7** — **completion:** numeric thresholds + eval. |
| **M4** | **T3d** (comment loop) + **T3b** (re-run triggers) | User comment may **either** stay in inner loop or **force** re-run; rules must assign cleanly to avoid ambiguous tooling. |
| **M5** | **T2c** (auto-skip) + **T5a** (populate boundary) | Auto-accept is unsafe if resolver can **name** entities that don’t exist yet—**A.11** caps what auto may do. |

No large **circular** block beyond these; the critical path is roughly **T1 → T2 → T3**, with **M1–M5** joint passes where noted.

---

## Part D — Suggested discussion order (meetings / threads)

1. **Thread 1:** ~~M1 / **A.5**~~ **done** (UI wiring in product specs).  
2. **Thread 2:** ~~T2b / **A.12** v1 contract~~ **done**; detail JSON when persisting.  
3. **Thread 3 (M2):** **T3b** + **T3c** — outer **trigger** matrix + **A.8** merge/replace + exhaustion (**A.9** **`R`** rule **done**).  
4. **Thread 4 (M3+M4):** **A.7** thresholds + eval (**M3**); **A.6** completion via **M4** (inner vs outer); **A.8**/**A.10** completion via **M2** overlap as needed.  
5. **Thread 5:** ~~**T4a / A.2**~~ **done** — **LLM-only** resolve accepted.  
6. **Thread 6 (M5):** T5a populate vs resolve with T2c auto policy (**T5b / A.14** resolved for prototype — **A.14**).  

---

## Part E — Changelog

| Date | Change |
|------|--------|
| 2026-04-05 | Initial doc: lifted assessment issues, tier order, mutual dependencies. |
| 2026-04-04 | A.1: `pre_resolved_nl` aligned with `statement_nl` unless real intermediate; A.4 confidence-gating note; **A.15** outcome states (draft); Part B/D refs T1c → **A.15**. |
| 2026-04-04 | **T1c / A.15** marked **resolved**: accepted state names; **`USER_ACCEPTED`** sub-fields = recommendation vs alternate structured choice (+ ids). |
| 2026-04-04 | **T1a / A.1** marked **resolved**. **T1b / A.4** resolved: one-call structured output, flag table, **2** validation re-prompts max, explicit retry triggers (pending `pipeline_spec.md` sync). |
| 2026-04-04 | **T2a / A.5** resolved (diff + free-text). **T2b / A.12** v1 trace contract. **T2c / A.3** partial (precedence). **T2d / A.9** partial: three budgets — validation retries (**A.4**), **`K=3`**, **`R=2`**; M2 gap remains. **M1** closed at design level. |
| 2026-04-04 | **T3** partials documented with **completion gaps:** **A.6** (M4), **A.7** (thresholds/M3), **A.8** (M2 merge), **A.10** (M2 matrix). **A.2 / T4a** assessment: v1 **LLM-always** recommended; hybrid deferred. Tier 3/4 tables + Thread 4/5 updated. |
| 2026-04-04 | **A.2 / T4a** **resolved:** **LLM-only** resolve for v1 (no hybrid rewrite branch). Thread 5 closed. |
| 2026-04-04 | **A.1** supplement: **`registry_resolution_candidate_nl`** (in-loop / provisional) vs committed **`registry_resolved_nl`**; **A.4**–**A.6**, **A.11**–**A.12**, **A.15**, **T1a** / **T5a** aligned. |
| 2026-04-04 | **T5b / A.14** resolved (v1 prototype): compliance via **A.3** / **`POLICY_REVIEW_REQUIRED`**; concurrency via session snapshot + no silent live merge / hard fail or re-run on stale refs. |
| 2026-04-04 | **T2c / A.3:** v1 **`AUTO_ACCEPTED`** predicate (strict); ε / **medium** auto deferred **A.7** / **M5**. **T2d / A.9** **resolved:** **`R`** only on outer re-pass. **M2** row narrowed. |
