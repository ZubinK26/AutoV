# Registry graph edges: design choices in plain language

This note is for readers who are new to **graphs** in a knowledge system. It explains what we mean by **“explicit graph edges”** between **rules** and **registry entries**, why we care, and what changes depending on which option we pick.

If you already know RDF triples or knowledge graphs, you can skim the analogies.

---

## 1. What problem are we solving?

Later in your pipeline you may want to ask questions like:

- “Which registry entries does **this rule** actually use?”
- “Which rules **mention** this predicate; which **depend** on it in a proof?”
- “What structure connects entry A to entry B?” (for contradiction search, explanation, or impact analysis)

You *could* answer those by **re-reading the natural-language rule** or **re-running** parts of the formalizer every time. That is slow, fuzzy, and hard to keep consistent.

**Explicit graph edges** mean: after you formalize or validate a rule, you **save** the links in a structured way (IDs in a list or a small table), so **search and tools** can walk the graph without guessing from text.

**Analogy:** A bibliography at the end of a paper is explicit edges from “this paper” to “these sources.” Without it, a reader would have to infer citations only by reading every sentence.

---

## 2. The two kinds of “things” we link

| Concept | Simple meaning | Example |
|--------|----------------|---------|
| **Rule** | One accepted line from WFM; becomes one row in the rules store (unless OUT_OF_SCOPE). | “Every cat is a mammal.” |
| **Registry entry** | One formal object in your registry: sort, predicate, constant, axiom record, etc., each with a stable **entry ID**. | Predicate `Mammal`, axiom `∀x (Cat(x) → Mammal(x))` |

An **edge** is a stored fact: **this rule** is linked to **these entry IDs** (and maybe rule↔rule or entry↔entry later).

---

## 3. Choice A — When do we “freeze” the edges?

Edges could be written at different pipeline moments. The question is: **when do we treat the saved links as the official record?**

### Option A1 — Right after “populate” (registry updated from the formalization)

**Idea:** As soon as new symbols or axioms are **created or matched** in the registry, we record which entry IDs the rule touched.

**Example effect**

- Rule formalizes to a new predicate `P` and a new axiom `A`.
- Immediately after populate, we store: `rule_42 → [entry_P, entry_A]`.
- If Z3 validation **fails** later, the rule might be rejected—but the **edges might already exist** unless we roll them back or mark them tentative.

**Pros:** You always know “what the formalizer tried to use,” good for debugging and replay.

**Cons:** Edges can include things that never become “accepted truth” if validation fails, unless you have a **status** or **two-phase** commit.

### Option A2 — Only after Z3 says OK (or after a defined “commit” point)

**Idea:** We only persist rule→entry edges when the rule is **accepted** (or when a transaction commits).

**Example effect**

- Same rule; populate creates `P` and `A`, but Z3 fails.
- **No** durable edges on the rule, or edges stay in a **draft** bucket.
- After fix + pass, we store `rule_42 → [entry_P, entry_A]`.

**Pros:** The graph reflects **what the system stands behind**, not every failed attempt.

**Cons:** You lose an easy “what did the last run touch?” trail unless you keep **separate** audit/draft links.

### Option A3 — Both: draft vs committed

**Idea:** Maintain **draft_edges** during the run; **copy to committed_edges** only on success.

**Example effect**

- Operators see draft links in logs or a staging UI; the public graph updates only on commit.

**Pros:** Best of both worlds for operations.

**Cons:** Slightly more schema and tooling.

**Beginner takeaway:** This choice is about whether the graph is a **lab notebook** (everything tried) or a **published map** (only what passed).

---

## 4. Choice B — What does one edge *mean*?

Not all “mentioned in the rule” is the same as “used in the proof,” and not all “used” is the same in semantics.

### Option B1 — One flat list per rule

**Idea:** `linked_entry_ids: [id1, id2, id3]` with no subtyping.

**Example**

```text
rule_42.linked_entry_ids = [pred_Cat, pred_Mammal, axiom_12]
```

**Effect**

- Simple to implement and to export.
- Harder to answer precise questions (“only axioms,” “only predicates mentioned in NL but not in FOL”) without extra heuristics.

### Option B2 — Split by *kind* of link

**Idea:** Separate buckets, e.g. `mentions`, `defines`, `used_in_formalization`, `depends_on_axioms`, or similar.

**Example**

```text
rule_42.entries_mentioned_in_nl = [pred_Cat, pred_Mammal]
rule_42.entries_in_fol_ast = [pred_Cat, pred_Mammal]
rule_42.entries_required_for_proof = [axiom_12, pred_Mammal]
```

**Effect**

- Heavier schema, but **clearer** reports and safer automation (“only bump proof deps when proof deps change”).

### Option B3 — Labeled edges (small edge table)

**Idea:** Each edge is a row: `(rule_id, entry_id, relationship)`.

**Example**

| rule_id | entry_id | relationship |
|---------|----------|--------------|
| 42 | pred_Cat | MENTIONED_IN_NL |
| 42 | axiom_12 | USED_IN_VALIDATION |

**Effect**

- Most flexible; easiest to add new relationship types later.
- Slightly more storage and query complexity.

**Beginner takeaway:** Flat is **easiest**; split columns or a **triple store** is **clearest** when you need different *meanings* of “linked.”

---

## 5. Choice C — Keeping “Source rule” and rule-side edges in sync

Your registry entries can carry **metadata** like “Source rule: &lt;rule_ref&gt;”. The rule side can carry **entry IDs**. If one updates without the other, you get **orphans** or **mismatches**.

### Option C1 — Registry is primary; rule edges are derived or mirrored carefully

**Idea:** Canonical “this entry came from this rule” lives on the **entry**; the rule stores IDs **for fast reverse lookup** but is updated in the **same transaction** as the entry.

**Effect**

- One mental model: “the entry knows its parent rule.”
- Must enforce: when entry’s source changes, rule’s list updates (or is regenerated).

### Option C2 — Rule is primary; entry’s Source rule is derived

**Idea:** The rule’s edge list is **authoritative**; entry metadata is **filled** from it on write.

**Effect**

- Good when one rule creates **many** entries; regeneration can restate source consistently.

### Option C3 — Event log / single writer

**Idea:** Neither side is edited alone; an **append-only event** (“RuleCommitted”) carries both sides; materialized views fill rule and entry fields.

**Effect**

- Best audit story; more engineering.

**Beginner takeaway:** Pick one **source of truth** or use a **log** so the two representations cannot drift silently.

---

## 6. OUT_OF_SCOPE lines (special case)

Lines marked **OUT_OF_SCOPE** are still in the **handoff** for provenance, but they **do not** get a formal rule row in the same way as accepted lines.

**Effect on edges**

- **No** (or empty) **rule→entry** edges on the rules side for that line, because there is no formalized artifact to anchor them—or you store edges only at **bundle** level for traceability.
- Registry entries that *would* have been created are **not** created for that line.

**Beginner takeaway:** The graph connects **formal** objects; OOS lines stay in the narrative envelope, not in the formal spine.

---

## 7. Choice D — Entry ↔ entry links (structure inside the registry)

Sometimes you want edges **between** entries: e.g. axiom A **instantiates** schema S; constant `c` **has sort** `T`; predicate P **subtype** of Q.

### Option D1 — Stored edges

**Idea:** Persist `entry_X → entry_Y` with a label.

**Effect**

- Fast graph queries, stable exports, clear versioning.
- Must **update** when entries merge, deprecate, or split.

### Option D2 — Computed on demand

**Idea:** Derive from fields already on entries (`sort`, `arity`, `defs`) without a separate edge table.

**Effect**

- Less duplication, but **harder** for ad-hoc relations not captured in fields.
- Every new structural question may need new **code** to recompute.

### Option D3 — Hybrid

**Idea:** Store **expensive or user-declared** relations; compute **cheap** ones.

**Effect**

- Practical default for growing systems.

**Beginner takeaway:** If you often ask “neighbors in the registry graph,” **store**; if structure is **fully determined** by columns you already have, **compute**.

---

## 8. Quick comparison — what you *feel* in the product

| If you mostly choose… | Day-to-day effect |
|----------------------|-------------------|
| Early edges + flat list | Easiest to ship first; queries are vague (“everything linked”). |
| Late edges + typed edges | Clearest **trusted** graph; best for auditors and contradiction tools. |
| Single source of truth + event log | Most consistent long-term; upfront cost. |
| No entry↔entry storage | Simpler DB; you may write one-off traversers later. |

---

## 9. Where this ties into your repo

- Pipeline shape, handoff, graph edges (**A3/B3/C1/D3**), rules↔registry alignment, and **failure / commit contract** are in **`pipeline_spec.md`**.
- High-level decision table (**#1–#7**, all **resolved**): **`Registry_Way_Forward.ipynb`**.

This note records **options and trade-offs**; **canonical** edge behavior is **Graph-friendly shape** in **`pipeline_spec.md`**.

---

## 10. Glossary (one line each)

| Term | One-line meaning |
|------|------------------|
| **Populate** | Write or match registry entries from the formalization of a rule. |
| **Z3** | An SMT solver; here, “does this formalization validate in the logic layer?” |
| **Commit** | The moment persisted state becomes official (often after validation). |
| **Entry ID** | Immutable identifier for one registry object. |
| **Graph edge** | Stored link between two IDs with an optional label or kind. |
