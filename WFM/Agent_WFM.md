# Workflow — Well-Formedness Module (WFM)



## What WFM is



Ensures **complete**, **unambiguous** (including coreference), and **within-scope** information is passed downstream.



**LLM instructions** for each internal agent live in **`prompts/`** (see `prompts/README.md`). This file defines **behavior and control flow**; prompts define **checklists and wording** sent to the model.



### Requirements vs. checks



| Area | Intent |

|------|--------|

| **Complete information** | LLM flags implicit or missing information. Prompts include examples and patterns; expand as needed *(see Open issues)*. |

| **Unambiguous information** | LLM flags ambiguity **including coreference**. Coreference is **not** a separate agent step; it is handled **under ambiguity**. |

| **Within-scope** | LLM flags against in-scope / out-of-scope patterns; scope lists are in the Agent 3 prompt and **`pipeline_spec.md`**. |



---



## Control flow (Agents 1–4)



Core LLM path: **Agent 1 → Agent 2 → Agent 3**, then the **confirmation (UI)** step. **Agent 4 (LLM)** runs only when the user **rejects** part or all of the package and supplies feedback. After an **approved merge** of revisions, WFM may be **re-run from Agent 1** on the **merged natural-language rule** (see **Confirmation package**, **Patch merge**, and **Reruns and exhaustion**).



### Agent 1 — Completeness and ambiguity (single LLM call)



**One call, two phases** (no separate sub-invocations required):



1. **Flag** — Emit flags for **completeness** and **ambiguity** (coreference is included **under ambiguity**, not as a separate category).

2. **Resolve** — In one pass, resolve **both** dimensions using the **most likely interpretation** and **guesses** where needed.



**Output:** Refined natural language only. **No metadata** is required or produced for any step **through decomposition** (through end of Agent 2). Downstream receives plain text suitable for Agent 2.



**Loop-back:** When WFM is re-entered after the user confirms a **merged rule** (see **Patch merge**), Agent 1 receives **only** that single NL document — no retry labels, no prior agent metadata, no line-level freeze hints unless product adds them later.



**Input length (safety only):** Before Agent 1, enforce **`max_input_code_points`** from **`config/wfm.json`** (this module: `WFM/config/wfm.json` from repo root). **Definition:** count **Unicode code points** (same idea as Python `len()` on a normal string). **Default value: 4096.**



**Why 4096:** A *medium* body paragraph is often on the order of **100–200 words**. Using ~5.5 characters per word (letters, digits, spaces, light punctuation), that is roughly **550–1,200** code points; dense or technical wording can land higher. **4,096** code points is a **generous** ceiling—well above a typical medium paragraph, with headroom for long phrases—while still bounding prompts. It is not expected to bind in practice; it is a safety rail.



If input **exceeds** the limit, **do not** run WFM: return to the **user input step** with a clear message (current count vs. limit, ask to shorten or **submit separate rules**). No automatic chunking, truncation, or multi-part merging.



---



### Agent 2 — Decomposition



Decompose statements toward **atomic** form, subject to a **compound-operator chain limit** (default **8**, **`compound_operator_limit`** in **`WFM/config/wfm.json`** — keep in sync with **`prompts/agent_2_decomposition.md`**; see **Decomposition (Agent 2)** in Reference below).



- If output would **exceed** the compound-operator limit: **terminate WFM**, **reset to the user input step**, and return an **error report from Agent 2** that includes a **structured diagnostic** (see Agent 2 prompt): the offending sub-statement(s) verbatim, **operator total vs budget**, and an **itemized operator trace** so the user can see how the count was obtained. Also include an **error message** stating that the limit was exceeded. The user-facing error **must** include this **hint line** (exact wording for consistency): *“Try turning this into several shorter rules and submitting them one at a time.”* The **orchestration layer** **must** ensure that exact sentence appears in the **final** user-facing message (it **need not** be produced by the Agent 2 model; the Agent 2 prompt may use diagnostics-only output and defer this line to the product layer).



**Loop-back:** Receives **only** the input text — no extra context that this is a retry.



---



### Agent 3 — Scope check and rewrite



- Perform scope check; flag issues in output.

- If a **within-scope rewrite** is possible that is **equivalent in this context to the original** (not a different-but-related rule): **minimize** change, produce the rewrite, and a **diff report** between input and rewrite (essential differences in simple terms). If nothing substantive changed, the diff should say so. The diff is always shown to the user in the **confirmation package**. **Unacceptable meaning change** means any change that fails that equivalence standard.

- If **no** rewrite can meet that standard: produce a **scope report** (no rewrite). Do **not** force a rewrite. Processing **continues** to the confirmation step with that report.



**Failed rewrite:** If Agent 3 **attempts** a within-scope rewrite but the rewrite **fails** per system or policy checks (e.g. validation, safety gate), **reset to the user input step** with an error reason — same class of recovery as other WFM hard failures. *(Exact failure conditions TBD in implementation.)*



**Loop-back:** Receives **only** the **same input class as a fresh run** — **Agent 2’s decomposed sub-statements** (plain text, typically numbered lines), with **no** retry metadata.



---



### Confirmation package (UI) — after Agent 3



After Agent 3, the user **always** receives a **confirmation package** built with **UI and templates** (no LLM required for the static view). It includes:



- The **decomposed sub-statements** (numbered lines), each tied to Agent 3’s outcome: **PASS**, **REWRITE** (with diff text where applicable), or **OUT_OF_SCOPE** (with scope explanation where applicable).

- Enough context for an informed decision: **diff** and **scope** material as specified in **`prompts/agent_3_scope_rewrite.md`** and orchestration.



**Accept-in-full (happy path):** If the user **accepts the entire package** without disagreeing on any line, **orchestration** proceeds to the **next pipeline stage** (e.g. registry). No Agent 4 LLM call is required for that path.



**Per-line disagreement:** The user may **disagree with one or more specific lines** (by index). **Each disagreed line must have its own comment** (non-empty), regardless of Agent 3 label on that line — including cases where the user disagrees because of **Agent 1 / Agent 2** behavior rather than Agent 3’s verdict. The UI may offer a shortcut (e.g. duplicate draft text into every selected row), but the system **still stores one comment per disagreed line**.



**Blanket rejection:** **Blanket** means **select all lines** as disagreed. **Same rule:** **one comment per line** (**N** comments for **N** lines). No single global comment substitutes for per-line comments in this mode.



**Implicit agreement on untouched lines:** Any numbered line **not** marked as disagreed is **accepted as shown** (including **REWRITE** text as presented). **Silence** on those lines means consent. **Do not** send accepted lines through Agent 4 for alteration; they are carried **verbatim** into **patch merge** (below).



**OUT_OF_SCOPE lines — no silent drop:** For every line marked **OUT_OF_SCOPE**, the user must leave a **recorded** outcome before merge and re-entry to WFM. Allowed outcomes:



1. **Pursue revision** — the line is **disagreed** with a **comment**; Agent 4 and/or user-driven text may supply a **replacement** intended to be in-scope, captured in the structured patch.

2. **Confirmed omit** — the user **explicitly confirms** that the line is **excluded** from the rule bundle that proceeds downstream (orchestration stores this; it is **not** inferred from ignoring the line).



There is **no** valid path where an **OUT_OF_SCOPE** line is dropped or skipped **without** either a **replacement** path or **confirmed omit**.



**Optional second confirmation:** After orchestration computes the **merged** rule text, the product **may** show a **final merged rule** preview. Once the user **confirms** that preview, the **merged NL** is what **re-enters** WFM at Agent 1. *(What happens if the user **rejects** that final preview is **not** yet specified — see **Open issues**; current placeholder: **abort** / reset to user input without an extended Agent 4 loop.)*



There are **no** inline markers in running text for speculative resolution; the user is **informed upfront** (via UI copy) that earlier steps may have used guesses. The package still reads as a **definitive proposal** pending user action.



---



### Agent 4 (LLM) — structured disagreement and patch



**When invoked:** After the user marks **disagreed lines** and supplies **per-line comments**, **or** after partial engagement that still requires Agent 4 assistance under product rules. **Not** used to render the initial confirmation package.



**Inputs (orchestration → model):** A **structured disagreement payload** should include at minimum: full **numbered list** as shown, **Agent 3 labels** per index, **disagreed indices**, **comments per disagreed index**, and any **confirmed omit** decisions already taken for **OUT_OF_SCOPE** lines (so the model does not invent omissions).



**Role:** Clarify objections in natural language (per **`prompts/agent_4_user_interaction.md`**), then produce **replacement wording only for disagreed indices** that are not **confirmed omit**. **Accepted lines must not be rewritten** by Agent 4 except as required to output a valid machine-readable patch (orchestration still **merges** using **verbatim** accepted text for non-patch indices).



**Machine-readable patch (`WFM_PATCH`):** The **model** supplies **`replacements`** only (see **`prompts/agent_4_user_interaction.md`**). **`omit_indices`** are **never** invented by the model: orchestration fills them from the user’s **confirmed omit** choices in the UI when building the **effective patch** for merge.



Effective patch object (conceptual — may exist only inside orchestration after validation):



```json

{

  "replacements": [ { "index": <1-based line number matching the confirmation UI>, "text": "<replacement sub-statement>" } ],

  "omit_indices": [ <1-based line numbers the user explicitly confirmed to omit> ]

}

```



**Rules:** **Indices are 1-based** and must match the **same numbering** shown to the user in the confirmation package. **Replacements** may **only** touch line indices the user **disagreed** with (and that are not user-confirmed omits). Orchestration **rejects** patches that alter non-disagreed lines or invent omits. The Agent 4 transcript must include a parseable **`WFM_PATCH`** block as defined in the Agent 4 prompt.



**Retry budget (unchanged):** **First exchange is free** — clarifying questions **and** first proposal that includes a valid patch (or patch-equivalent). **Then 3 retries** total. Each retry = **one** proposal, **optionally** preceded by **one** clarifying question; each retry **must end in a proposal** (see decision table).



**Inner exhaustion:** If the Agent 4 tentative-rewrite budget is exhausted without an **orchestration-valid** patch and user confirmation to proceed → **WFM failure**: **reset to user input** with reason.



---



### Patch merge and re-entry to WFM



**Programmatic merge (orchestration):** Apply `replacements` and `omit_indices` to the **authoritative numbered list** from the confirmation snapshot — i.e. the **per-line text as shown** in the package (**PASS** = verbatim Agent 2 line unless the UI displayed otherwise; **REWRITE** = rewritten text as displayed; plus user-approved **WFM_PATCH** replacements and **confirmed omits**). Lines neither replaced nor omitted remain **byte-identical** to that accepted display text.



**NL document for re-run (Style A — canonical):** After applying replacements and omitting confirmed lines, **renumber consecutively** from **1** through the remaining count. Build **one** string for **Agent 1** by joining each sub-statement as a line **`N. `** + text + **newline** (`\n`), for **N = 1 … count** (trim final trailing newline optional but **must** be applied **consistently** everywhere merge runs for reproducibility). **No** other join style is used for loop-back unless this document is formally revised.



**Re-run:** **Agent 1 → Agent 2 → Agent 3** on that merged string, subject to the **outer** full-WFM rerun budget (**1 initial + 3 reruns** unless changed).



**Records:** The system should retain originals, Agent 1–3 traces, user comments per line, patch JSON, merged NL, and confirmation timestamps for audit.



---



## Reruns and exhaustion



- **Full WFM reruns** after an agreed tentative rewrite: budget **1 initial run + 3 reruns** (**4** total full passes) unless product changes this constant.

- **Outer exhaustion:** If the full WFM rerun budget is exhausted without success → **WFM failure**: **reset to user input** with an **error message** explaining reason (same pattern as inner exhaustion).



**No internal loops** except Agent 4’s tentative-generation loop, which has its own independent limit as above.



**Clarification (UI vs LLM):** The user **always** sees the post–Agent 3 **confirmation package** (via **UI / templates**). **LLM-mediated** Agent 4 interaction (questions, tentative rewrites) applies **after** the user responds — **typically when they say no** and supply comments. That is **not** a contradiction: presentation is a product step; the **LLM** is not required to render static confirmation content.



---



## Loop-back from end of WFM



**Agreed merged** natural language (after confirmation, optional patch flow, and **programmatic merge**) goes **back to Agent 1** as **fresh** input. Agents **1–3 do not** know it is a retry. **Accepted** sub-statements are already **embedded verbatim** in that string from merge; expectations of immutability are enforced in **orchestration**, not by metadata passed into Agent 1.



The **Agent 4 LLM** **does not** inject extra context into Agents 1–3 on loop-back — **accepted limitation**: deep LLM engagement occurs in the **reject / patch** phase only.



---



## Decision table (resolved control-flow items)



| Topic | Resolution |

|-------|-------------|

| Agent 2 compound limit exceeded | Reset to **user input**; **Agent 2 error report** (verbatim offending sub-statement(s), **operator count vs budget**, **itemized operator trace** per Agent 2 prompt) + **error message** (limit exceeded); include hint: *“Try turning this into several shorter rules and submitting them one at a time.”* (**orchestration** must ensure this exact line is in the **final** user-facing message — see Agent 2 section). |

| Agent 4 inner retry budget exhausted | **WFM failure**; reset to **user input** with **reason**. |

| Outer WFM rerun budget exhausted | **WFM failure**; reset to **user input** with **reason**. |

| Agent 4 retry counting | First exchange **free** (questions + first rewrite); then **3 retries**; each retry = **one** proposal, **optionally** one preceding question; **must end in proposal**. |

| Agent 1 structure | **Single call**: **flag** (completeness + ambiguity, coref under ambiguity) → **joint resolve** (most likely interp + guesses). **No metadata** through decomposition. |

| Agent 3 outputs | **Scope report** when no rewrite; **diff report** when rewrite offered. User always sees these in the **confirmation package**. |

| Agent 3 failed rewrite | **Reset to user input** with error reason. |

| Loop-back / Agent 4 | Agents 1–3: text only. **Confirmation package** after Agent 3 (UI). **Agent 4 LLM** after user **rejects** lines and supplies comments; **accept-all** skips Agent 4. No injection into early agents on loop-back. |

| Long / multi-paragraph input (safety) | **`max_input_code_points`** (default **4096**, `WFM/config/wfm.json`); measure **Unicode code points**; **reject** over limit before Agent 1; **no** auto-chunk/truncate. |

| Per-line disagreement | User may disagree with **specific indices**; **each disagreed line requires its own non-empty comment**. |

| Blanket rejection | **Select all lines** as disagreed; still **N comments for N lines** (UI may duplicate draft into N fields). |

| Implicit agreement | Any line **not** disagreed is **accepted as shown**; **REWRITE** text as displayed counts as accepted if untouched. |

| **OUT_OF_SCOPE** handling | **No silent drop.** For each OOS line: either **replacement** path (disagree + comment → patch) or **user-confirmed omit** recorded by orchestration (`omit_indices`). |

| Patch merge before re-run | **Model (`WFM_PATCH`):** JSON with **`replacements` only** (see Agent 4 prompt). **Orchestration:** merges user **confirmed omit** indices into the **effective** patch, **validates** (no edits to non-disagreed lines), applies merge, builds **Style A** NL; optional **final merged** preview; then **Agent 1** on that string. |

| Final merged preview rejected | **Open** — not fully specified; placeholder: **abort** / reset to user input; **no** additional Agent 4 retry loop defined yet. |



---



## Open issues (not yet specified in product detail)



| Topic | Status |

|-------|--------|

| **Prompt maintenance** | Baseline instruction packs live in **`prompts/`**. Agent 3 output format is **machine-pinned** (`PASS|REWRITE|OUT_OF_SCOPE: N. "…"`) for merge and tooling; add edge-case types and examples as traffic reveals gaps. |

| **WFM test harness (repo)** | **`test_sets/scripts/`**: Gemini Agents 1–3 (`run_wfm_folio_gemini.py`), Agent 4 from JSONL + merge preview with **Agent 3–aware** base (`run_wfm_agent4_from_run.py`, `wfm_agent4_common.py`), interactive Agent 4 (`run_wfm_agent4_interactive.py`), loopback **merge preview → Agents 1–3** (`run_wfm_loopback_agent4_merge.py`). Not the product orchestrator; documents in **`test_sets/README.md`**. |

| **Decomposition meaning drift** | **Accepted risk** for now; user may catch downstream; optional future checkpoint. |

| **Full-pipeline failure contract** | **WFM exit** (limits, exhaustion, return-to-input) and **WFM↔orchestrator** event shape remain **TBD** at API level. **Post-WFM** persistence (commits to `registry.json` / `rules.json` / `bundles/`, full vs partial bundle, draft vs committed) is specified in **`pipeline_spec.md`** — *Failure / commit contract (resolved)*. |

| **Reject final merged rule preview** | If the user **rejects** the post-merge **final NL** confirmation, define **retry policy** (whether Agent 4 re-engages, budget, and prompt updates). **Current:** treat as **abort** / return to user input until specified. |

| **`WFM_PATCH` prompt details** | **Done** in **`prompts/agent_4_user_interaction.md`**; keep in sync with **Patch merge** here. |



---



## Reference: architecture and definitions



- **WFM architecture:** Four internal roles: (1) completeness + ambiguity resolution, (2) decomposition, (3) scope check + rewrite/reports, (4) **UI confirmation package** after Agent 3 plus **conditional Agent 4 LLM** for structured disagreement, **`WFM_PATCH`**, and merge before optional full WFM re-run.

- **Speculative resolution marking:** None in text; user informed upfront (e.g. UI copy); output shown as definitive proposal for confirmation.

- **Decomposition (Agent 2):** Goal is the **smallest sub-statements that still preserve meaning**, with each piece within the **compound-operator limit** and the **plain-language counting rules** in **`prompts/agent_2_decomposition.md`**. If a part is **splittable into independent claims without losing meaning**, it is **not** fully decomposed yet (subject to Agent 2 counterexamples about conditionals). Operational definition and examples: **Agent 2 prompt**.

- **After WFM:** Cleaned output is confirmed with the user, then passed to the **registry agent** (per pipeline spec in the repo root). **Structured handoff** (bundle id, per-line `statement_nl`, Agent 3 verdicts, scope/diff reports, `agent2_line_text`, timestamps, optional package-level Style A NL) is defined in **`pipeline_spec.md`** — **WFM → registry handoff (orchestration payload)**.



This document is the **source of truth** for WFM behavior; **`pipeline_spec.md`** aligns to it.

