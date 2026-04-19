# NL→Z3 pipeline — plain-language companion

**Companion to:** `control_flow_v1.md`  
**Purpose:** Describe the **same** control flow in approachable language, define **technical terms**, and give a **linear walkthrough** without assuming a PL/formal-methods background.

---

## What problem does this pipeline solve?

People write **natural-language rules** (English). The system turns each accepted rule into **executable logic** using the **Z3** solver (via **Python**), and stores **definitions** of the symbols (names for sorts, objects, functions) in a **registry** so the same ideas can be **found** and **reused** later.

---

## Glossary

| Term | Plain meaning |
|------|----------------|
| **WFM (workflow / confirmation stage)** | A prior step where the text is **cleaned**, **split into lines**, and marked **in scope** or **out of scope** for this logic pipeline. This document **starts after** that step, when the user has **accepted** the bundle. |
| **Bundle** | One **batch** of lines that were accepted together. Has an id (`bundle_id`) and **ordered** lines (`line_index`: 0, 1, 2, …). |
| **IN_SCOPE / OUT_OF_SCOPE** | **In scope** = “try to formalize this line.” **Out of scope** = **skip** formalization; keep the line only as **metadata** (e.g. for audit). |
| **Formalizer** | An **LLM** that writes **Python code** which uses the **Z3** library to express the line’s meaning. |
| **Z3** | A **solver**: software that answers questions like “can these constraints **all** hold at once?” (**SAT** = yes, there is a model; **UNSAT** = no, they contradict; **UNKNOWN** = gave up or time limit). |
| **Sandbox** | Running the generated script in a **controlled** environment: **only** safe imports (here: **z3**), **time limit**, **no network** — so bad code cannot **harm** the machine. |
| **SAT / UNSAT / UNKNOWN** | **SAT** = constraints are **jointly satisfiable**. **UNSAT** = **impossible** to satisfy them all. **UNKNOWN** = solver did not decide. In this design, **UNSAT is not automatically a “bug”** — it is **recorded** like SAT. **Repair** is for **crashes** and **timeouts**, not for UNSAT by itself. |
| **Registry** | A **database** (here: JSON files) of **named logical items**: sorts (types), constants (named objects), functions (relations and operations). Each item has a stable **`id`** and a human-style **`canonical_name`** used for **lookup** and **uniqueness**. |
| **Canonical name** | The **official** snake_case name stored in the registry (e.g. `michael`, `taller_than`). **Rules A–G** apply to **these** names. |
| **Z3 string literal** | The **text inside quotes** when you create a Z3 symbol, e.g. `DeclareSort('person')` → the literal is **`person`**. The **same real-world idea** might appear as **different** literals on **different** lines; the **registry** can still **link** them by **reusing** the same **`entry_id`**. |
| **Symbol bindings** | A **table** for **one line**: “this **literal** in the code **maps** to **reusing** this existing registry entry **or** **creating** a new one.” **Every** literal the **extractor** finds must have **one row**. |
| **Extractor** | A **small program** (not an LLM) that **reads** the Python file and **lists** the Z3 name strings in **allowed** places (e.g. `DeclareSort`, `Function`, `Const`). It keeps validation **predictable**. |
| **Registry agent** | An **LLM** that **decides** reuse vs new names, using **tools**: exact name lookup, signature lookup, **semantic search** (find similar meanings via **embeddings** — vectors of text meaning). |
| **Embedding** | A **numeric vector** representing a piece of text so that **similar** texts have **similar** vectors. Used for **semantic search** (“things that **mean** alike”). |
| **Semantic search** | Search by **meaning**, not only **exact** text match. |
| **Programmatic validation gate** | **Automated checks** (schema, naming rules, **extractor** vs **bindings**, **reuse** correctness, **ambiguity** rule). **No** human in the loop in v1. |
| **Ambiguity check** | If the **validator** runs the **same** semantic search the agent uses and finds **two** strong matches **close** in score, the agent must **explicitly** say which it **chose** or **why** it created a **new** name anyway — **or** the line goes to **repair**. |
| **Repair loop** | **Try again** with a **clear error message** (bounded number of tries). **Not** a human escalation in v1. |
| **Isolated line theory** | Each line’s script is run **alone**. Line 2 does **not** automatically **see** the axioms from line 1 in the **same** solver run. The **bundle** is still **linked** through **shared registry ids** and **metadata** in the product sense. |
| **Commit** | **Writing** successful rules and registry updates to disk **atomically** (all succeed or none visible). |

---

## Linear walkthrough (what happens in order)

1. **Start from a WFM bundle**  
   You have **lines** with text, **verdicts**, and ids.

2. **Split by scope**  
   **Out-of-scope** lines are **skipped** for the rest; **in-scope** lines go forward.

3. **Formalizer**  
   For each in-scope line, an LLM writes **one Python file** that uses **Z3**. It does **not** see the registry yet.

4. **Sandbox run**  
   The code runs in a **safe** environment.  
   - If the **Python process crashes**, **times out**, or **breaks policy** → **repair** the formalizer (retry, up to a limit).  
   - If it **finishes** and **calls** `check()` → record whether the answer was **sat**, **unsat**, or **unknown**. **None** of those **by itself** triggers “fix the formalizer” — **only** **execution** failure does.

5. **Registry agent**  
   For each line that has **good** code, another LLM **reads** the code and the **natural-language** line and fills in **`symbol_bindings`**: for each literal the **extractor** would find, **reuse** an existing registry entry or **propose** a **new** one with a **canonical name** obeying **A–G**.

6. **Validation gate**  
   Programs check: JSON shape, **every** extracted literal **covered**, names **legal**, reuse **really** matches signatures, and **ambiguity** rules **if** two close semantic matches exist. If something fails → **registry repair** loop (bounded).

7. **Commit**  
   Successful lines **write** rules and registry entries. Failed lines are **listed** on the bundle **without** undoing successes.

---

## How to read this next to the formal spec

- **`control_flow_v1.md`** = **contract** (exact fields, failure categories, **rules**).  
- **This file** = **orientation** and **vocabulary**.  
If something **conflicts**, the **formal spec** wins.

---

## End of companion
