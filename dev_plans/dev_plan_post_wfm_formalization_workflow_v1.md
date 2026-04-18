# Dev plan: post-WFM formalization → consolidation → registry (v1 draft)

**Status:** Draft — not yet merged into canonical design docs (`pipeline_spec.md`, phase plans, etc.).  
**Purpose:** Spell out what we need to implement the workflow discussed in chat: **complete NL→Z3 formalization first** (readable names, structured notes), **then** deduplication / resolution / **populate** from **deterministic parse** of stabilized code.  
**Entry point:** Immediately **after WFM completes** for a bundle (structured lines, WFM verdicts, handoff payload as today).

---

## 1. Goals (non-negotiables)

| Goal | What “good” looks like |
|------|-------------------------|
| **Formalization effectiveness** | NL lines become **executable Z3** (Python) that is **locally consistent** per bundle; failures are **explicit** (no fake `print("UNSAT")` posing as solver output). |
| **NL ↔ formalization mapping** | Every formalized line has **stable references**: `line_index`, `statement_nl`, **artifact** (source text), and **identifier manifest** produced with the formalization. |
| **Exact search** | Find **duplicate or near-duplicate** NL (and later, normalized term shapes) within the bundle and across bundles **deterministically** where possible. |
| **Semantic search** | Find **paraphrases** / similar intent when exact match fails; used to **cluster** candidates for human or model review—not as sole proof of identity. |
| **Evaluation effectiveness** | Each search hit is routed through a **small, explicit decision procedure** (below) so we don’t improvise per case in code. |
| **Automated rename** | When policy says **exactly two** competing symbols are **α-equivalent** (same structure, rename-only) **and** evaluation selects a **canonical name**, apply **mechanical** replacement in code **without** another open-ended LLM pass. |

---

## 2. Pipeline phases (order locked)

1. **WFM ends** → inputs frozen: ordered lines, WFM metadata, bundle id.
2. **Formalization pass (per line or per bundle chunk)**  
   - LLM emits: `z3_python_source`, **`identifier_notes`** (see §3), optional `llm_rationale_short` (debug only).  
   - **No registry id string-matching requirement** at this stage.  
   - Z3 execution / smoke checks as today (exit code, no uncaught exceptions).
3. **Bundle correspondence store**  
   - Persist: `{ bundle_id, line_index, statement_nl, z3_python_source, identifier_notes, hashes, timestamps }`.  
   - This is the **source of truth** until consolidation finishes.
4. **Consolidation pass (exact → semantic → evaluate)**  
   - Operates on **stored formalizations + NL set** for the scope we define (bundle-first; cross-bundle optional).  
   - Outputs: **canonical name decisions**, **rename map**, **conflict list** requiring human or escalated model review.
5. **Apply renames (automated where policy allows)**  
   - Transform Z3 source text or AST-backed edit; re-run Z3 **once** per changed artifact to confirm **behavior unchanged** (see §6).
6. **Registry populate (deterministic)**  
   - Parse **final** Z3 code → sorts, consts, function symbols, arities, domain/codomain sorts.  
   - Link to **NL lines** and **bundle id**; **exclude** long-lived storage of per-entity “why I named it this” if it becomes **stale** after renames (or store versioned / debug-only).

---

## 3. Artifacts to specify (schemas — implementation later)

### 3.1 `identifier_notes` (required output of formalization)

For **each** identifier introduced in `z3_python_source`:

- **Local name** (as in code).  
- **Kind:** sort | const | function | variable (bound) — **bound vars may be omitted** from registry if policy says “no skolem in registry.”  
- **Arity** (functions) and **sort signature** (domain/codomain).  
- **One sentence:** which **NL phrase(s)** it models and **why** this sort vs predicate choice was made.

This supports **evaluation without re-LLM-ing** the whole formalization for every search hit.

### 3.2 Normalized forms (for comparison — not for human display)

Define **one** internal representation for “same structure, different names” checks, e.g.:

- Parse Python → extract Z3 constructor calls **or** run a **normalization** pass (TBD: avoid rabbit hole—start with **structural hash** of AST of Z3-building subset).

**Flag for confirmation (FC-1):** v1 compares **within-bundle** only, or **cross-bundle** from day one? Cross-bundle explodes edge cases; recommend **bundle-first**, then **optional** corpus index.

---

## 4. Search layer

### 4.1 Exact search (deterministic)

- **NL:** normalized whitespace/case/punctuation; optional **stemming** off for v1 (keep off to reduce false merges).  
- **Code:** structural hash / normalized term tree **after** stripping Python variable names per `identifier_notes`.

**Use:** find **true duplicates** and **rename-only** duplicates cheaply.

### 4.2 Semantic search (retrieval)

- **Embeddings** over `statement_nl` + short **summary** of `identifier_notes` (not full Z3).  
- **Retrieve top-k** candidates; never auto-merge on similarity alone.

**Use:** feed **evaluation** with “maybe same intent” clusters.

**Flag for confirmation (FC-2):** embedding model + hosting (local vs API) and **privacy** if NL is sensitive.

---

## 5. Evaluation: scenarios and required actions

We separate **(A) identity of meaning** from **(B) identity of symbol**.

### 5.1 Dimensions

- **Structural equivalence (Z3):** same quantifier structure, same connectives, same function graph **up to renaming** of uninterpreted symbols.  
- **Identifier qualities:** arity, sort, function vs sort confusion, **overloading** (same local name, different binding sites).  
- **NL:** exact vs paraphrase vs **related but different** (scope, quantifiers, “every” vs “some”).

### 5.2 Scenario matrix (what to do)

Rows are **search channels**; columns are **what differs**.

| ID | Situation | Action |
|----|-----------|--------|
| **E1** | Exact NL match + **structural match** + **rename-only** difference | **Auto-canonicalize** per policy (§7): pick **canonical name** (longest-stable rule: first occurrence, or **human default** list). **Automated replace** in code. |
| **E2** | Exact NL match + structures **differ** | **Do not auto-rename.** **Escalate:** either **human** or **constrained LLM** chooses **which formalization is wrong** or **both** need re-formalization. **Never** merge registry entries. |
| **E3** | Semantic NL match (high score) + **structural match** + rename-only | Same as **E1**, **if** secondary gate passes: **paraphrase checker** (small LLM **yes/no**: “same proposition?”) **or** human tick. **If gate fails** → treat as **E4**. |
| **E4** | Semantic NL match + structures **differ** | **Escalate** like **E2**; retrieval is **only** a hint. |
| **E5** | Same **local identifier name** in two lines but **different arity/sort** in `identifier_notes` or parse | **Treat as conflict** (likely **accidental name collision**). **Do not** unify without renaming **at least one** symbol. **Automated** proposal: suffix `_2` on later line **only if** structures unrelated; else **escalate**. |
| **E6** | Different NL + **structural match** (duplicate theory) | **Deduplicate documentation** (link lines to same canonical formalization id); **optional** single canonical code copy in storage. **Names** follow **E1** if rename-only between copies. |
| **E7** | Exact or semantic hit, but one side **failed** Z3 / incomplete | **Exclude** from merge; **re-formalize** failed lines first. |

### 5.3 “Differences in other qualities of identifiers” (explicit)

| Case | Meaning | Action |
|------|---------|--------|
| **Q1** | Same intended concept, **different sorts** (e.g. `Person` vs `Carrier`) | **Not** a safe automatic merge. Options: **rejected** for v1 auto-merge; **escalate** with **sort coercion** story (out of scope unless we add a **typed repair** phase—**flag FC-3**). |
| **Q2** | Same name, **different arity** | **Q5** path: collision; escalate. |
| **Q3** | Predicate vs function-into-sort modeling | **Do not** auto-unify; **evaluation** only. Possible outcomes: **keep both** (different theories), **re-formalize** one line, or **add** bridge axioms (**later**; not v1 rabbit hole). |
| **Q4** | **Constants** vs **variables** (same spelling) | Parsing/binding analysis; usually **escalate** if structures differ. |

---

## 6. Automated identifier replacement (when only two choices)

**Preconditions (all required):**

1. **Structural match** + **rename-only** (or approved paraphrase gate for **E3**).  
2. **Canonical name** chosen by **deterministic rule** from **E1/E3** (no free-form LLM pick).  
3. **Single-file / known scope**: replacements limited to **declarations and uses** of that symbol in the **bundle’s stored sources** (no cross-file until we have **whole-program** scope).  
4. **Regression:** after replace, **run Z3**; **stdout** behavior policy: `check()` result **unchanged** for **conjunctive** bundles **or** document **allowed** changes if theory order changes (v1: require **unchanged** `sat`/`unsat` **per line** if isolated—**FC-4**: do we formalize **per-line isolated** scripts only?).

If any precondition fails → **no automation**; go to **escalation**.

---

## 7. Canonical naming policy (deterministic)

Default proposal for v1 (tunable):

- Among α-equivalent copies, prefer **first line index**’s names **or** **longer, more descriptive** local name **if** tied—pick **one rule** and stick to it.  
- **Never** rename **bound** variables unless **normalization** step does it internally (not persisted).

**Flag for confirmation (FC-5):** product preference for **first-wins** vs **longest-readable-wins**.

---

## 8. Registry populate (after consolidation)

- **Input:** **final** Z3 sources + **line mapping** + **rename audit log**.  
- **Parse:** deterministic extraction of symbols (no LLM).  
- **Store:** `entry_id` generation from **content hash + bundle** (or stable uuid) — **separate** from LLM local names; link table maps **local canonical name** → **entry_id**.  
- **Exclude from durable registry:** free-form **per-identifier rationale** if it **references** pre-rename strings; keep **versioned debug** blob if needed.

---

## 9. Gaps and non-goals (avoid rabbit holes)

| Topic | v1 stance |
|-------|-----------|
| **Bridge axioms** between incompatible sorts | **Out of scope** — escalate only. |
| **Full proof** that two NL sentences are logically equivalent | **Out of scope** — use **structural** match + **cheap** LLM gate for paraphrase. |
| **Minimal / optimal** theory | **Out of scope** — only consistency and dedup. |
| **Interactive** “mid-bundle” registry | Optional **session-local** symbol table; **no** durable registry until phase 6. |

---

## 10. Open questions — please confirm

1. **FC-1:** Consolidation **bundle-only** for v1, or **cross-bundle** from day one?  
2. **FC-2:** Embedding stack and **on-prem** requirement?  
3. **FC-3:** Any appetite for a **typed repair** phase in the next iteration, or keep **escalation-only** for sort mismatches?  
4. **FC-4:** Are formalizations **always** **one line = one isolated script**, or **one script** for the **whole bundle**? This changes regression checks for automated rename.  
5. **FC-5:** **First-wins** vs **longest-readable** canonical naming?  
6. **FC-6:** When **escalation** triggers, is the default **human review** or **constrained LLM** with **mandatory** human approval?

---

## 11. Implementation kickoff checklist (engineering)

- [ ] Freeze **WFM output contract** (already exists — verify nothing missing for line-indexed NL).  
- [ ] Define **JSON schema** for `identifier_notes` + **validation** in CI.  
- [ ] **Formalization** prompt v2: readable names + notes; **forbid** fake solver output.  
- [ ] **Bundle store** (filesystem or DB) for formalization artifacts.  
- [ ] **Exact** + **semantic** index builders (bundle scope first).  
- [ ] **Normalizer** for Z3 Python subset + **tests** with golden pairs (rename-only).  
- [ ] **Rename applier** + **Z3 regression** runner.  
- [ ] **Populate** from parse + **link** table to NL.  
- [ ] **Audit log** for every automated rename (before/after hash).

---

*End of v1 draft.*
