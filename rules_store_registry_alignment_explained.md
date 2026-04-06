# Why the “rules store” and the “registry” must agree (issue #6, explained simply)

This note is for readers who are **new** to the project’s data layout. It explains **what problem #6 is solving**, **without assuming** you already know terms like `rules.json`, “labeled edges,” or “issue #4.”

**Status:** Rules-store ↔ registry alignment (**#6**) and the rest of the registry design table (**#1–#7**) are **resolved** in **`pipeline_spec.md`**.

- **#6** — subsection **Rules store ↔ registry alignment (resolved)**.
- **#7** — subsection **Failure / commit contract (resolved)** (`bundles/{bundle_id}.pipeline.json`, user-directed partial commit, etc.).
- **Full WFM handoff:** **`bundles/{bundle_id}.json`** next to `registry.json` / `rules.json` (**no per-rule `handoff_ref`** by default).
- **Rule-level semantic embeddings:** **deferred** until **contradiction / candidate-search** work.

Summary table: **`Registry_Way_Forward.ipynb`**. This file remains the **plain-language** companion for **#6**.

---

## 1. Two notebooks that must tell the same story

Imagine your system keeps information in **two separate notebooks**:

### Notebook A — the **registry** (often saved as something like `registry.json`)

This is the **dictionary of formal “things”** your logic talks about:

- Sorts (types), like “Animal”
- Constants, like “fluffy”
- Predicates / functions, like “is a mammal” with the right inputs

Each item gets a **stable ID** (a short code that never gets silently recycled for a different meaning — that was an earlier design decision about **identity**).

Each item can also record **which user rule(s)** led to it being there or reused — think of it as **“provenance”** or **“this line in the confirmation package is responsible for this symbol.”**

### Notebook B — the **rules store** (often saved as something like `rules.json`)

This is the **list of accepted formal rules** — one row per **line** the user actually committed after checks (after WFM, registry work, formalization, and the solver check).

Each row typically carries:

- The **cleaned sentence** for that line
- The **formal representation** (e.g. Z3-style code) that was accepted
- **Which bundle** of lines it came from (one user “acceptance” can contain several lines)
- **Links** to the registry items that rule actually **uses** or **created** — so you can jump from “this rule” to “these dictionary entries” without re-reading everything from scratch

**The broad problem #6 addresses:**  
If Notebook A and Notebook B **disagree** — e.g. the rule says it uses entry `ent_7`, but the registry says `ent_7` was never tied to that rule, or two lists of links get out of sync — then **search, debugging, future “does this contradict that?” tooling, and even simple UI** become unreliable.

So #6 is **not** a new feature request. It is the work of saying clearly: **what is written where, and how we keep the two notebooks consistent.**

---

## 2. What we already decided (so you know what #6 builds on)

Earlier choices (sometimes labeled #1–#5 in internal docs) set **constraints** you do not re-litigate in #6:

- **Identity:** IDs are **stable**; we don’t quietly reuse an ID for something else.
- **Granularity:** One **formal rule row** per **accepted confirmation line**; many lines from one user acceptance share a **bundle id** so you know they arrived together.
- **Handoff from WFM:** The pipeline passes **structured** fields (verdict per line, text per line, bundle id, timestamps, etc.), not only free-form prose.
- **How rule↔registry links work:** **Draft** links may exist while the system is still checking; **only after success** do **official (“committed”)** links count for normal tools. Links are **labeled** (e.g. “appears in the formal formula” vs “mentioned in natural language”) so a computer knows **what kind of connection** it is, not just “some connection.” **Registry entries** carry the **authoritative** “which rule(s) this entry is tied to,” and the **rule side** keeps a **matching list for quick lookup**, updated in the **same save** so they don’t drift. Some **entry-to-entry** links are **stored**; simple ones can be **worked out from fields** when needed.

#6 assumes all of that. It answers: **given those rules, exactly how do we lay out Notebook A and Notebook B on disk so developers don’t trap themselves?**

---

## 3. The core tension in one sentence

**The registry** is organized around **“things”** (symbols, axioms-as-entries, etc.).  
**The rules store** is organized around **“assertions the user committed”** (one per line).

The **same fact** (“rule 12 uses registry entry 45 with meaning X”) might be **derivable** from both sides. #6 is about **recording that fact once clearly** (or twice **on purpose** as a **controlled copy**) so nothing **contradicts** and nothing is **forgotten** when you save.

---

## 4. What “files” means here (JSON, JSONL)

You might see **`rules.json`**, **`registry.json`**, or suggestions like **`rule_edges.jsonl`**.

- **`.json`** usually means one big structured text file the program can load as a tree (objects and arrays). Good for “whole snapshot on disk.”
- **`.jsonl`** (JSON Lines) means **one small JSON record per line** — handy for **many edge rows** (millions of links) or streaming writes.

**#6 does not require** a specific filename. It requires **agreement** on whether links live **inside** `rules.json`, in a **separate** edges file, or both — and **which copy is the “boss”** when they disagree after a bug.

---

## 5. The decisions to make (each one in plain English)

Below, each item is **a real fork** someone implementing the system must resolve. Think of them as **house rules for the two notebooks**.

### Decision 1 — One main place for “rule → registry links” vs a deliberate duplicate

**Situation:** You need to store many facts like: “Rule 12 —(kind of link)→ Registry entry 45.”

**Fork:**

- **Option A — One primary place** for all those link rows (e.g. one edges file or one section of a file). A rule row only stores **ids like rule id and bundle id**, and **tools join** the data when showing “what this rule touches.”
- **Option B — Copy the same links** onto each rule **and** keep a global list (two places **on purpose**, like an address in your **contacts app** and again on the **calendar event** — convenient, but they must stay identical).

**Why it matters:** If you pick B without discipline, one copy updates and the other doesn’t — **silent disagreement**. If you pick A, **every** tool must know to look in the right place.

**What #6 needs:** A written rule: **which layout you use**, and **if duplicated, how you detect/fix drift** (e.g. “rebuild the list on the rule from the registry”).

---

### Decision 2 — What exactly goes on each “rule row”

**Situation:** Each accepted line becomes one **rule record** with text, formal code, bundle membership, etc.

**Fork:** **Extra** fields — audit ids, counts, timestamps, pointers back to the WFM handoff — vs keeping the row **minimal**.

**Why it matters:** **Reporting** (“show me this acceptance”) and **debugging** want bundle context; **bloat** makes every reader slower and invites fields that **duplicate** graph data in a third shape.

**What #6 needs:** A **minimal agreed checklist** of fields per rule row so every engineer reads the same spec.

---

### Decision 3 — One list of links or “flat list” **and** labeled list

**Situation:** An older design might say “store a **flat** list of entry ids.” A newer design says each link has a **label** (what the relationship **means**).

**Fork:** Support **only** labeled links (recommended to avoid two truths), or keep both **and** define which one tools must trust.

**Why it matters:** If both exist and differ, **contradiction tools** or **impact reports** will disagree and nobody will know which is right.

**What #6 needs:** **One** official representation for links in the committed (official) world.

---

### Decision 4 — When a registry entry is **reused** by a **new** rule

**Situation:** Rule 1 introduced predicate `P`. Later, Rule 9 uses the **same** `P` again. The registry entry for `P` should **know** both rules (provenance). The **new** rule should get links like “appears in formalization,” but **not** incorrectly claim “I created this predicate from scratch” if it didn’t.

**Why it matters:** Wrong **labels** confuse cleanup (“if I remove Rule 9, can I delete `P`?” — only if no other rule needs it). **Stable IDs** mean reuse is normal; **semantics** must stay honest.

**What #6 needs:** Written rules for which **labels** apply when an entry **already existed** vs when it was **created** in this run.

---

### Decision 5 — Do we also store a **“bundle”** record separately?

**Situation:** One user click can accept **several lines** at once — same **bundle id**, several **rule ids**.

**Fork:** A **bundle header** object (one per acceptance listing rule ids in order) vs **only** repeating `bundle_id` on each rule and **inferring** the group in code.

**Why it matters:** **Rollback**, **audit exports**, and **UI** (“show the whole acceptance”) get easier with an explicit bundle object; skipping it saves a little complexity **if** you never need those features.

**What #6 needs:** **Yes/no** on bundle records, and if yes, **what fields** they carry (without duplicating huge payloads).

---

### Decision 6 — Search embeddings on **rules** (optional)

**Situation:** The registry usually has **semantic search** (vectors) over **descriptions of symbols**. You might or might not want **semantic search over rules** (“find rules like this sentence”).

**Why it matters:** This is **mostly separate** from alignment, but if you add it, you must define **what text** gets embedded so results stay sensible.

**What #6 needs:** Usually **defer** unless you have a product requirement; if yes, **one** embedding policy for rules.

---

### Decision 7 — If something goes wrong, who is “legally right”?

**Situation:** Even with “save both together,” bugs happen.

**Fork:** Clear **recovery story** — e.g. “**Registry `source rule` fields are the truth for ownership**; **labeled edge rows are the truth for relationship types**; we have a script to **rebuild** the convenient copy on the rule from those.”

**Why it matters:** Without this, on-call debugging becomes **arguments about JSON** instead of **one documented repair path**.

**What #6 needs:** A **short precedence order** and **one** rebuild direction documented for implementers.

---

## 6. What you are **not** deciding in #6

- **How** WFM works (that’s upstream).
- **Whether** you use draft vs committed links (already decided — draft is scratch, committed is official).
- **Whether** embeddings exist for registry search (already in the broader design — **dual retrieval**: structure + vectors).

#6 is specifically **persistence layout + consistency rules** between **the dictionary** and **the committed rules list**.

---

## 7. Glossary (plain definitions)

| Term | Simple meaning |
|------|----------------|
| **Registry** | The **dictionary** of formal entities (sorts, constants, predicates/functions, etc.) with stable **IDs**. |
| **Rules store** | The **list of accepted formal rules** (often one **row** per **confirmation line** that passed checks). |
| **Bundle** | One **user acceptance event** that may contain **several lines**; lines share a **bundle id**. |
| **Rule id** | Stable id for **one** committed rule row (one line). |
| **Entry id** | Stable id for **one** registry object. |
| **Link / edge** | A stored fact connecting a **rule** to a **registry entry**, optionally with a **label** (what kind of connection). |
| **Draft vs committed** | **Draft** = work in progress during checks; **committed** = official after success. |
| **`source rule` (on an entry)** | **Authoritative** note of which rule(s) the registry associates with that entry (provenance / ownership story). |
| **Mirror** | A **second copy** of some facts for convenience (e.g. links duplicated on the rule), must stay **identical** to the authoritative side after each save. |
| **`rules.json` / `registry.json`** | **Example filenames** for the two notebooks — your project could merge or split files; the **idea** is two logical stores. |
| **JSON / JSONL** | Text file formats for machines; JSON is one tree, JSONL is **one record per line**. |
| **Issue #6** | Project shorthand for “**align rules store and registry** — layout + consistency.” |

---

## 8. Mental picture to keep

1. **Registry** = **ingredients** in the kitchen, each labeled **where they came from**.  
2. **Rules store** = **recipes** the diner actually put on the menu.  
3. **#6** = **recipe cards say which ingredients they use, in the same handwriting as the ingredient bins** — or you have **one central ledger** everyone agrees is official.

Once that feels obvious, you understand the **general problem** #6 solves: **no two authoritative stories** about the same rule and the same symbols unless **one is clearly a copy** of the other and **kept in sync.**
