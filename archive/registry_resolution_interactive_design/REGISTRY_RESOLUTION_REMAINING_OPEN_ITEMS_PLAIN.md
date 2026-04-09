# Registry resolution — what’s still open (plain English)

> **Archived (2026-04-04):** Companion to the archived design-issues doc. **Phase 1:** **`../../development_plan_registry_stage_v1.md`** — *Automated LLM resolution*.

**Purpose:** Explain **only the parts that are not fully “done”** in `REGISTRY_RESOLUTION_DESIGN_OPEN_ISSUES.md` (same folder), in everyday language. Use this to see **why** the design doc grew so many branches, and to decide what can move into **`development_plan_registry_stage_v1.md` (M0–M6)** or **empirical work** so this companion file can shrink over time.

**This doc does not replace** the design open file; it **summarizes residual risk and ambiguity**. The dev plan is **not edited** here—only **suggested merge targets** are listed.

---

## Why it feels like “so many decisions appeared”

You described a workflow that is simple in words—**search → gaps → resolve → maybe user → maybe re-search**—but in software every phrase hides **state machines**:

- **Who** is allowed to skip the user, and **when**?
- **What counts** as a failed answer from the model vs a **legal** answer you disagree with?
- **What happens** if the user changes the sentence but you **don’t** re-embed the registry?
- **What do you call** text that is **not** yet “officially” resolved?

Each of those became a **named issue** (A.x / Tiers / mutual-dependency sets) so implementation wouldn’t guess wrong. Many items are **already decided** in the design doc; what remains is mostly **numbers from testing**, **wiring in code**, or **product appetite for risk**.

---

## How to read the classifications

Each open item is tagged with one or more of:

| Tag | Meaning |
|-----|--------|
| **E — Empirical** | You’ll answer it mainly by **running tests / eval / trying prompts**, not by thinking harder on paper. |
| **D — Dev plan / execution** | Belongs as **concrete work** under M0–M6 (or a follow-up ticket), not as an eternal design mystery. |
| **U — User / product** | Needs a **value judgment**: how much automation risk to accept, what tenants must see a human, etc. |

---

## Tier-by-tier: what is **not** fully finished

*(Tiers **without** entries here are **fully resolved** in the design doc for v1 prototype purposes.)*

### Tier 2 (still partially open)

#### **A.3 — When can we auto-accept without showing the user?**

- **Plain problem:** The model might say “I’m sure,” but **you** still need rules for when that is **good enough** to skip a person. If the rules are too loose, you ship wrong registry text; if too tight, you **never** get speed benefits.
- **What’s already settled:** A **strict** v1 list of conditions for **`AUTO_ACCEPTED`** (policy first, no provisionals, `needs_human_review` false, `confidence_tier` high, etc.).
- **What’s still open:** Looser rules later—e.g. **“top two matches almost tied”** (**ε**), allowing **`medium`** confidence to auto in some tenants, extra “never auto if …” rows.
- **Classification:** **E** (measure error rates; tune thresholds), **U** (how aggressive auto-skip may become per tenant), **D** (encode final rules in **M4** resolve + config; may **reopen** “done” checklist rows in the dev plan when you add tenant knobs).

---

### Tier 3 (all four items are still partly open)

#### **A.6 — Inner loop: user comments feeding the resolver**

- **Plain problem:** The user can steer the resolver several times (**K** rounds). You still need **crystal-clear rules** for: *this* feedback **stays in the inner loop* vs *this* feedback **must trigger a full re-search / outer pass* (**R**). Without that, engineers guess—and you get endless loops or wrong inventory.
- **What’s already settled:** **What** gets sent back to the model each round (bounded package: candidate NL, frozen vs open spans, short summary). **Not** letting the model alone order an outer re-run.
- **What’s still open:** Exact **if / then** routing (**M4** in the design doc), especially at **K** exhaustion.
- **Classification:** **U** (edge-case behavior), **D** (**M4 — Resolve + user path** in dev plan—may need explicit tasks for “outer vs inner” once you implement).

#### **A.7 — Guardrails (“don’t break WFM / don’t invent ids”)**

- **Plain problem:** You need **automatic checks** so bad model output is **rejected or sent to review**—not silently accepted. The **ideas** for checks exist (surface distance, WFM scope, ids in session, duplicates); the **sensitivity** of each check is numeric.
- **What’s already settled:** **What kinds** of checks to run (layers).
- **What’s still open:** **How strict** (ε, edit limits, embedding margins). Wrong numbers = false accepts or false rejects.
- **Classification:** **E** (calibrate on fixtures + eval set—dev plan already expects **M3 empirical validation**; guardrails land in **M4** when resolve validates candidates).

#### **A.8 — After “Jeff vs Jeffrey”: re-search and history**

- **Plain problem:** When you **re-run search** from scratch, you get **new** hits. You must decide how the **current working** list of hits relates to the **old** one, while **audit** still shows **every** past attempt.
- **What’s already settled:** **Stable `line_index`**, append-only snapshots, no silent deletion of history.
- **What’s still open:** **Merge vs replace** of the **live** retrieval set the resolver uses **this hour** (design **M2** mutual set / implementation choice).
- **Classification:** **D** (implement when you build outer re-run in **M4/M5** traces), **U** (prefer **simplicity** vs **recall**—e.g. replace working set but keep history in trace).

#### **A.10 — Who is allowed to say “we need a full re-search”?**

- **Plain problem:** The model might **want** fresh embeddings; you don’t want it to **burn** outer budgets (**R**) on a whim. So **who** flips `OUTER_RERUN_TRIGGERED` must be **code + policy**, not vibes alone.
- **What’s already settled:** Governance: **deterministic/policy** commits **R**; **seed list** of situations (inventory mismatch, new name not in session, user asks re-search, …).
- **What’s still open:** **Complete** trigger matrix and how it interacts with **K** exhaustion and canned outcomes (**design M2**).
- **Classification:** **D** (**M4** implementation + tests), **U** (optional triggers like “match quality collapsed” after **A.7** exists).

---

### Tier 5 (populate boundary — not marked “resolved” in the tier table)

#### **A.11 — New entities before populate**

- **Plain problem:** The resolver can **propose** names that **don’t exist** in the registry yet. You must decide how those live in **`registry_resolution_candidate_nl`**, when they’re allowed to become **`registry_resolved_nl`**, and how **populate** creates rows **without** lying in traces.
- **What’s already settled:** **Provisional** semantics; **no** committed **`registry_resolved_nl`** until a real commit path; structured markers in resolver output (keys still to implement).
- **What’s still open:** **Persistence** of placeholders, **draft** session rows, and whether any tenant may **AUTO_ACCEPT** with **some** provisionals (**M5** + **A.3**).
- **Classification:** **U** (risk on auto with provisionals), **D** (**M5 — Populate** + trace schema in dev plan).

---

### Cross-cutting (not a single A.x “tier,” but not fully closed)

#### **A.4 — Reason codes vs measured thresholds**

- **Plain problem:** Codes like **MAPPING_AMBIGUOUS** refer to “above a threshold”; the **enum** is decided, the **cutoff numbers** are not.
- **Classification:** **E**, **D** (prompt + validation in **M3/M4**).

#### **A.12 — Audit JSON: exact field names / nesting / redaction**

- **Plain problem:** You know **what dimensions** to log; you haven’t locked **exact** JSON keys for every store.
- **Classification:** **D** (**M1**/persistence + **M5** export—implementation detail, not philosophy).

#### **A.13 — `pipeline_spec.md` out of date**

- **Plain problem:** The narrative spec still mixes older wording (**e.g.** side-by-side without **`registry_resolution_candidate_nl`**) with your newer vocabulary.
- **Classification:** **D** (documentation pass—could be its own small task before or after **M4**).

---

## What can move **off** this design concern list (merge / handoff)

When you **slot** the work below into **M0–M6** (or an eval notebook), you can treat the corresponding rows as **execution backlog**, not “mystery design,” and **de-emphasize** them inside `REGISTRY_RESOLUTION_DESIGN_OPEN_ISSUES.md` if you want that file to stay high-level.

| Topic | Suggested home | Why it can leave “pure design” |
|-------|----------------|--------------------------------|
| **Search quality, masking, expansion defaults** | **M3** empirical block (already in dev plan) | Decided by measurement, not debate. |
| **Guardrail numbers (A.7)** | **M3** eval + **M4** validation code | Same: tune with data. |
| **Resolve loop wiring, inner vs outer, user menus** | **M4** | That milestone *is* the resolve state machine. |
| **Provisionals, traces, `registry_resolved_nl` commit** | **M5** | Populate + trace bundle owns persistence semantics. |
| **Demo / harness behavior** | **M6** | Forces honest end-to-end behavior. |
| **`pipeline_spec.md` vocabulary sync (A.13)** | Doc / Phase-1 polish task | Editorial alignment, not new product theory. |
| **Looser auto-accept (ε, medium tier) (A.3 tail)** | Post–prototype config + eval | Requires **A.7** data and **U** risk choice. |

**Items that stay “design + product” until you decide:** anything tagged **(U)** above—especially **automation appetite**, **provisionals + auto**, and **exact outer-trigger policy** when two reasonable behaviors exist.

---

## What you should still expect to feel “heavy”

Even after merging into M0–M6, **resolution** is heavy because it is a **small product** inside step 3: budgets, audit, two kinds of “NL,” and two loops. The design doc branched because each branch prevents a **class of bugs**. Moving work into the dev plan **does not shrink** the work—it **names** it so you’re not carrying it as unnamed anxiety.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-04 | Initial companion doc: plain-language remaining issues T1–T5, classifications, merge candidates to M0–M6. |
