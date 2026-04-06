# When A3, B3, C1, and D3 are built: what it actually looks like

This document is for you if the **design options** felt abstract. It describes **observable behavior** once those options are implemented: what shows up in data, what workflows feel like, what you **gain**, and what you **do not** get (so consenting to build this does not feel like signing a blank check).

Decisions assumed here:

| Letter | Choice | One-line meaning |
|--------|--------|------------------|
| **A3** | Draft **and** committed edges | During a run, links can exist in a **draft** form; only after success do they become **committed** (the “official” graph). |
| **B3** | Labeled edges (small table) | Each link is **rule_id + entry_id + relationship** (and maybe timestamp), not one anonymous list. |
| **C1** | Registry entry owns parentage | Each registry entry that “belongs” to a rule carries **source rule** (authoritative). The rule also stores links **for fast lookup**, updated **in the same commit** so they do not contradict the entries. |
| **D3** | Hybrid entry↔entry | Some structural links between entries are **stored**; others are **computed** when needed from fields already on the entries. |

Nothing here is code. It is a **picture of the finished behavior**.

---

## 1. The main fear this addresses

**Fear:** “I agreed to a graph, and now I will get something heavy, fuzzy, or LLM-driven that scans my whole database per rule.”

**What you are actually building (with B3 as we discussed):** Links are produced by **pipeline stages** (formalization, what gets sent to the solver, registry writes). Labels mean **operational things** like “this ID appeared in the formula” or “this entry was created while processing this rule,” not “an AI guessed a philosophical relation.”

**Fear:** “I will not know what is ‘real’ vs ‘experiment’.”

**What A3 does:** **Draft** is explicitly **not** the public graph. Queries and contradiction tools **default to committed**. Draft exists for **debugging and forensics** (what did a failed attempt touch?).

---

## 2. End-to-end: one rule, what happens on screen and on disk

Imagine one **accepted confirmation line** (after WFM): “Every cat is a mammal.” The orchestrator runs registry search → gap resolution → populate → formalize → Z3 → (assume) success → **commit**.

### 2.1 While the run is in progress (A3: draft)

**Behavior you can implement toward:**

- The system may record **draft edges** such as:
  - `(rule_7, entry_Cat, APPEARS_IN_FOL)` — the predicate for Cat appeared in the formalized formula.
  - `(rule_7, entry_Mammal, APPEARS_IN_FOL)`
  - `(rule_7, entry_axiom_501, CREATED_BY_RULE)` — a new axiom row was created for this line.

These sit behind a **draft** flag or a separate draft store. **Your product’s default “graph browser” or “impact view” should ignore them** so users do not treat undone work as truth.

**What you are not losing:** You still have **logs** of the run; draft edges are an **optional structured** view of “what populate was aiming at” before validation finished.

**What you gain:** When Z3 fails, you can answer “which registry IDs were already touched?” without re-running the formalizer—if you expose draft to operators or support.

### 2.2 If Z3 fails

**Behavior:**

- **No promotion** to committed. Draft may be **kept for debugging** or **discarded** per your retention policy.
- **Committed** graph: **unchanged** for this rule (no new official links).
- Registry policy (separate from this doc) decides whether **partial writes** roll back; A3 does not magically fix bad transactions—you still want a **clear commit boundary**.

**Significance:** Consenting to A3 is **not** consenting to corrupt published state; it is consenting to **carry structured scratch work** until you explicitly commit.

### 2.3 If Z3 succeeds: commit (A3 + C1)

**Behavior:**

1. **Registry entries** that this rule created or updated now have **`source_rule_id = rule_7`** (or equivalent). That field is **authoritative** for “who owns this object in the narrative of the pipeline.”

2. **Rule-side index:** `rule_7` gets **mirrored** links—either the same labeled rows now marked **committed**, or a copy into the “official” store. **Invariant:** every entry that says `source_rule_id = rule_7` should appear on **some** committed edge from `rule_7` to that entry (for navigation), and rule-side edges should not point at entries that **contradict** source fields.

3. **Default queries** (contradiction prep, “what does this rule touch?”) read **committed** only.

**What you are not losing:** You do not lose the ability to say “this axiom came from rule 7”; that stays on the **entry**.

**What you gain:** Fast “from rule → all entries” without scanning the whole registry every time—**as long as** the mirror is maintained in the same commit as the entries (your agreed C1 addition).

---

## 3. What B3 looks like in practice (labeled edges)

Instead of `rule_7 → [id1, id2, id3]` with no meaning, you have **many small facts**, for example:

| rule_id | entry_id     | relationship     | lifecycle |
|---------|--------------|------------------|-----------|
| rule_7  | entry_Cat    | APPEARS_IN_FOL   | committed |
| rule_7  | entry_Mammal | APPEARS_IN_FOL   | committed |
| rule_7  | entry_axiom_501 | CREATED_BY_RULE | committed |
| rule_7  | entry_Hair   | MENTIONED_IN_NL  | committed |

(Exact label names are implementation details; the **idea** is a **closed set** known to your code, not open English.)

### 3.1 What each kind of label is *for* (significance)

- **MENTIONED_IN_NL** — “The user’s words referred to this symbol.” Useful for explanations, UI hover, **not** always the same as logical dependence.
- **APPEARS_IN_FOL** (or similar) — “The formal object references this registry ID in its structured formula.” Tight link to **what the formalizer output**.
- **CREATED_BY_RULE** — “This registry row exists because this rule was processed.” Ownership and cleanup.
- **LOADED_FOR_VALIDATION** (if you add it) — “This was part of the Z3 problem for this check.” Often **subset of** or **close to** appears-in-FOL plus inherited theory.

**Contradiction-oriented search:** You can **prefer** edges that represent **logical pressure** (formula + validation context) over **pure NL mentions**, so you do not chase red herrings from informal wording.

### 3.2 What you are *not* buying with B3

- You are **not** getting automatic philosophical typing (“this *supports* that in a debate sense”). You get **engineering labels** tied to pipeline artifacts.
- If a label is **wrong**, it is a **bug in a deterministic step**, not “the model was vague”—which is easier to test and fix.

### 3.3 What you might “lose” vs a flat list (B1)

- Slightly **more storage** and **more rows**.
- Slightly **more** schema and UI if you want to **filter by label**.

**What you gain:** Without B2/B3, everything is a soup; anything serious (contradiction, impact) re-derives meaning or uses fragile heuristics. **B3 is the option where the meaning is explicit in the data.**

---

## 4. C1 with co-updated mirrors: daily life

### 4.1 Authoritative vs convenient

- **Authoritative:** “Entry `entry_axiom_501` has `source_rule_id = rule_7`.” If you delete or tombstone the rule per your product rules, you **know** which entries are orphans of that narrative.
- **Convenient:** “`rule_7` has outgoing edges to all entries it owns / uses.” **Clicking the rule** in a tool shows the bundle of registry objects without a full-table scan.

### 4.2 If they drift (what you fear)

**If** someone updates only one side in a bug, you can **detect** inconsistency: e.g. an entry claims `source_rule_id = rule_7` but there is no committed edge from `rule_7` to that entry. Your repair strategy can be **rebuild rule index from entries** (C1’s safety net).

**Significance of consenting to C1:** You are **not** trapping yourself—the entry metadata is the **ground truth** for parentage; the rule index is a **performance and UX** layer that must stay in sync **by process and tests**, not by hope.

---

## 5. D3 hybrid: entry↔entry — what is stored vs computed

### 5.1 Computed (typical)

Examples of things often **derivable** from fields on a single entry or pair of entries without a separate edge table:

- Constant `fluffy` has **sort** `Animal` (read the constant entry’s `sort_id`).
- Predicate **arity** / domain sort list (read the predicate entry).

**Behavior:** A graph tool **walks** those fields when it needs “constant → sort.” **No extra edge rows.**

### 5.2 Stored (typical)

Examples where **storing** an edge pays off:

- **Axiom A instantiates schematic axiom schema S** (a relationship that is not one simple field).
- **This theory fragment imports that fragment** (library structure).
- **Merged / deprecated / alias** links after registry cleanup—things you **query often** and do not want to re-derive from historical logs every time.

**Significance:** Consenting to D3 is **not** “store every possible graph.” It is **store the edges your tooling will actually traverse for logic search**; compute the boring mechanical ones.

### 5.3 What you “lose” by not storing everything (D1 everywhere)

- First version might **miss** some useful traversals until you learn which queries are hot.
- You add stored edges **when needed**, not upfront.

**What you avoid:** A huge edge table that duplicates information already in columns—double maintenance and confusion.

---

## 6. OUT_OF_SCOPE lines (unchanged agreement)

**Behavior:**

- Still in the **handoff package** for provenance.
- **No** formal rule row / **no** committed **rule→entry** graph spine for that line (unless you add a **bundle-level** only trace, which is optional).

**Significance:** The **formal graph** stays honest: it only connects **formalized** commitments.

---

## 7. “What am I saying yes to?” — short checklist

If you approve implementation of **A3 + B3 + C1 + D3** as described, you are saying yes to roughly this **runtime story**:

1. **During** processing, **draft** labeled links may exist; **default product behavior** treats them as non-authoritative.
2. **After** successful validation and **commit**, **committed** labeled links exist and tie **rules** to **entries** with **specific meanings** per label.
3. **Entries** carry **authoritative source rule**; **rules** carry a **mirror** of links updated **together** with entries.
4. **Some** entry↔entry links live in an edge store; **others** are **computed** from entry fields when tools need them.

You are **not** saying yes to:

- An LLM that classifies arbitrary relations by reading the whole registry per rule.
- A single flat list where every link means “¯\\_(ツ)_/¯ something.”
- Draft data **replacing** committed data in serious queries without an explicit operator mode.

---

## 8. After it exists: what feels different for you

| Before (no explicit graph) | After (this design) |
|----------------------------|---------------------|
| “Which IDs did this rule affect?” → re-run reasoning or grep NL | Committed edges answer from **data**; draft helps **diagnose failed runs**. |
| “Is this connection ‘real’ or ‘just English’?” → unclear | **Label** tells you (NL mention vs FOL vs created-by-rule). |
| “Entry says one thing, rule index says another” → chronic drift | **C1** + same-commit updates; **rebuild** rule index from entries if needed. |
| “Every graph question needs new ad-hoc code” | **B3** gives a stable place to attach **semantics** testers care about. |
| “Store duplicate edges for sort-of-parent every time” | **D3** keeps storage focused on **non-obvious** structure. |

---

## 9. Minimal mental model to keep

Think of three **layers**:

1. **Draft notebook** — “What we tried and what we touched” (A3).
2. **Published map** — “What we assert after checks” — committed B3 + C1 mirrors + chosen D3 stored edges.
3. **Field-derived facts** — cheap **computed** links (D3) so you do not freeze every trivial relation in amber.

If that picture matches what you want operators and future contradiction tooling to see, you have a concrete basis for consent—not just abstract letters.

---

## 10. Status

Registry / rules-store design choices **#1–#7** are **resolved** in **`pipeline_spec.md`** (including *Graph-friendly shape*, *Rules store ↔ registry alignment*, and *Failure / commit contract*). See **`Registry_Way_Forward.ipynb`** for the summary table.
