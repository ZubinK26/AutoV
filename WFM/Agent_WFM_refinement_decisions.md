# `Agent_WFM.md` — refinement decision table

**Scope:** Align [`Agent_WFM.md`](Agent_WFM.md) with current prompts and implementation choices.  
**Status:** Row resolutions **implemented** in `Agent_WFM.md` (see file for canonical text).

| ID | Issue | Status | Resolution |
|----|--------|--------|------------|
| WFM-1 | Reference: informal “atomic” definition | **Implemented** | Reference bullet **Decomposition (Agent 2)** matches Agent 2 prompt (goal, limit, counting, splittability). |
| WFM-2 | Agent 3 loop-back | **Implemented** | Loop-back: **Agent 2’s decomposed sub-statements**, same class as fresh run, no retry metadata. |
| WFM-3 | Agent 4 UI vs LLM | **Implemented** | Confirmation package via **UI/templates**; **LLM Agent 4** after user response (typically **no** + comments); clarification block + Reruns section note updated. |
| WFM-4 | Agent 3 meaning wording | **Implemented** | **Equivalent in this context**; minimize change; diff; unacceptable change = fails equivalence. |
| WFM-5 | Agent 2 hint / orchestration | **Implemented** | User-facing hint unchanged; **orchestration** must ensure exact line in final message; model may defer (Agent 2 section + decision table). |

---

## Cross-reference (optional follow-up)

- **`pipeline_spec.md`**: If it still describes Agent 4 only as an LLM-presenter, consider a one-line sync with UI-first wording.
