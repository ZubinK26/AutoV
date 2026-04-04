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



Linear pipeline: **Agent 1 → Agent 2 → Agent 3 → Agent 4**. Full WFM may be **re-run** from Agent 1 after user agreement on a revised statement (see **Reruns and exhaustion**).



### Agent 1 — Completeness and ambiguity (single LLM call)



**One call, two phases** (no separate sub-invocations required):



1. **Flag** — Emit flags for **completeness** and **ambiguity** (coreference is included **under ambiguity**, not as a separate category).

2. **Resolve** — In one pass, resolve **both** dimensions using the **most likely interpretation** and **guesses** where needed.



**Output:** Refined natural language only. **No metadata** is required or produced for any step **through decomposition** (through end of Agent 2). Downstream receives plain text suitable for Agent 2.



**Loop-back:** When WFM is re-entered after user agreement on a rewrite, Agent 1 receives **only** the agreed statement — no retry labels, no prior agent metadata.



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



### Agent 4 — User-facing presentation and feedback



After Agent 3, the user **always** receives the **confirmation package**: the **speculatively** completed, disambiguated, **decomposed** output plus **scope outcome** — either the **diff report** (when Agent 3 proposed a rewrite) or the **scope report** (when no rewrite was proposed), each with a **short, clear summary** of the issue(s) where applicable.



**Presentation (UI):** The application shows this package with **UI and templates** — an LLM call is **not** required for static display.



**Agent 4 (LLM):** The **LLM-mediated** Agent 4 step is invoked **after the user responds** — in the chosen product flow, **typically when the user rejects** the package and **provides comments**. It has access to **other agents’ goals** and **conversation history**; it may ask **clarifying questions** and propose **tentative rewrites** that aim to pass WFM and reflect user intent. **Retry budget (exact rule):** **First exchange is free** — questions **and** first rewrite proposal. **Then 3 retries** total. Each retry = **one** rewrite proposal, **optionally** preceded by **one** question; each retry **must end in a proposal**.



**User confirms (yes):** Proceed to the **next pipeline stage** (e.g. registry agent). **Acceptance** may be handled entirely by **orchestration** without an Agent 4 LLM turn. The cleaned output is always confirmed before leaving WFM.



There are **no** inline markers in the text for speculative resolution; the user is **informed upfront** (via UI copy) that completion/disambiguation may use guesses. The package reads as a **definitive proposal** for confirmation.



**Clarification:** For the **LLM**, **Agent 4 becomes active** when the user **rejects** and engages in feedback — not for the initial templated presentation. The **confirmation step** itself still happens for every run after Agent 3.



On **agreement** on a tentative statement: **re-run WFM from Agent 1** with that text. The system **records**: original user statement, transformed LLM outputs along the path, user comments, and **agreed** rewrite.



**Inner exhaustion:** If the Agent 4 tentative-rewrite budget is exhausted without agreement → **WFM failure**: **reset to user input** with an **error message** explaining reason.



---



## Reruns and exhaustion



- **Full WFM reruns** after an agreed tentative rewrite: budget **1 initial run + 3 reruns** (**4** total full passes) unless product changes this constant.

- **Outer exhaustion:** If the full WFM rerun budget is exhausted without success → **WFM failure**: **reset to user input** with an **error message** explaining reason (same pattern as inner exhaustion).



**No internal loops** except Agent 4’s tentative-generation loop, which has its own independent limit as above.



**Clarification (UI vs LLM):** The user **always** sees the post–Agent 3 **confirmation package** (via **UI / templates**). **LLM-mediated** Agent 4 interaction (questions, tentative rewrites) applies **after** the user responds — **typically when they say no** and supply comments. That is **not** a contradiction: presentation is a product step; the **LLM** is not required to render static confirmation content.



---



## Loop-back from end of WFM



**Agreed** tentative statement goes **back to Agent 1** as **fresh** input. Agents **1–3 do not** know it is a retry.



The **Agent 4 LLM** **does not** inject extra context into Agents 1–3 on loop-back — **accepted limitation**: deep LLM engagement occurs when the user **rejects** the Agent 3-era result and supplies comments.



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

| Loop-back / Agent 4 | Agents 1–3: text only. **Confirmation package** after Agent 3 (UI). **Agent 4 LLM** after user response (typically **no**). No injection into early agents on loop-back. |

| Long / multi-paragraph input (safety) | **`max_input_code_points`** (default **4096**, `WFM/config/wfm.json`); measure **Unicode code points**; **reject** over limit before Agent 1; **no** auto-chunk/truncate. |



---



## Open issues (not yet specified in product detail)



| Topic | Status |

|-------|--------|

| **Prompt maintenance** | Baseline instruction packs live in **`prompts/`**. Add edge-case types and extra examples as real traffic reveals gaps. |

| **Decomposition meaning drift** | **Accepted risk** for now; user may catch downstream; optional future checkpoint. |

| **Full-pipeline failure contract** | Registry / formalizer must accept a single **WFM failure / return-to-input** signal and messaging; detailed API TBD. |



---



## Reference: architecture and definitions



- **WFM architecture:** Four internal agents: (1) completeness + ambiguity resolution, (2) decomposition, (3) scope check + rewrite/reports, (4) user-facing presentation (**UI** for confirmation package) and **conditional LLM feedback** when the user rejects and engages.

- **Speculative resolution marking:** None in text; user informed upfront (e.g. UI copy); output shown as definitive proposal for confirmation.

- **Decomposition (Agent 2):** Goal is the **smallest sub-statements that still preserve meaning**, with each piece within the **compound-operator limit** and the **plain-language counting rules** in **`prompts/agent_2_decomposition.md`**. If a part is **splittable into independent claims without losing meaning**, it is **not** fully decomposed yet (subject to Agent 2 counterexamples about conditionals). Operational definition and examples: **Agent 2 prompt**.

- **After WFM:** Cleaned output is confirmed with the user, then passed to the **registry agent** (per pipeline spec in the repo root).



This document is the **source of truth** for WFM behavior; **`pipeline_spec.md`** aligns to it.

