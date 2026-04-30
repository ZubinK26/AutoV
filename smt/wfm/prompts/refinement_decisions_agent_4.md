# Agent 4 prompt — refinement decision table

**Scope:** [`agent_4_user_interaction.md`](agent_4_user_interaction.md)  
**Architecture (chosen):** The confirmation package is shown with **UI + templates** (Agent 3 output, scope material, yes/no). The **Agent 4 LLM** is **not** called for that static screen — only **from the user’s response onward** (typically **no** + comments). This keeps policy aligned with `Agent_WFM.md` while avoiding pointless API calls for read-only presentation.

**Structured handoff and re-run:** After rejection and comments, Agent 4’s **user-facing** reply must be paired with a parseable **`WFM_PATCH`** block (JSON **`replacements` only**; UI supplies **confirmed omits** to orchestration). Orchestration **merges** programmatically, then builds the **Style A** natural-language document (`1. …\n2. …\n`, consecutive numbering) that is the **sole input** to the next Agent 1 pass — see **`../Agent_WFM.md`** (Confirmation package, Agent 4, Patch merge) and the walkthrough **`../../test_sets/wfm_agent4_confirmation_manual_scenario.md`** (repo-relative from this file: `test_sets/…` at project root).

| ID | Topic | Status | Resolution |
|----|--------|--------|------------|
| A1 | Proposed reading vs guarantee | **Implemented** | **FRAMING** block: single proposed reading; not guaranteed without review; gaps / chosen readings may have been filled earlier; plain language. |
| A2 | Sequencing / no premature rewrites | **Implemented** | **HOW YOU ARE INVOKED** + **YOUR JOB** point 1: UI shows package first; engage from user response; no opening rewrite before engaging with **stated** objection (unless enough to act). |
| A3 | Full thread + goal summaries on rejection | **Implemented** | **WHEN THE USER REJECTS** bullet: full thread + brief internal summaries; no agent/pipeline names to user. |
| A4 | Scope/diff ordering | **Implemented** | **WHEN YOU MENTION SCOPE OUTCOMES**: always one-sentence summary, then full diff or scope text. |
| A5 | Yes path / handoff | **Resolved — no prompt change** | Orchestration; LLM may not run on accept. |
| A6 | Outer WFM budget | **Resolved — no prompt change** | Orchestration-only. |
| A7 | Forbidden vocabulary edge cases | **Deferred** | No change. |

---

## §1 — Historical note (spec vs implementation)

`Agent_WFM.md` still describes “Agent 4” as the **logical** confirmation phase (presentation + conditional negotiation). **This implementation** splits that into **templated UI** (presentation) and **LLM** (negotiation and rewrites after user response). No open product contradictions if the UI carries the same obligations: show full package, require comments on reject, and include the **FRAMING** notice (or equivalent) on the template.

---

## §2 — Optional: UI template checklist (for implementers, not model copy)

Ensure the confirmation screen includes:
- Decomposed rule text and scope outcome (diff / out-of-scope) with **summary sentence then full report** for any scope block.
- Plain-language notice that text is a **proposed reading** and may reflect **guesses** for gaps or ambiguity — user should **review** before accepting.
