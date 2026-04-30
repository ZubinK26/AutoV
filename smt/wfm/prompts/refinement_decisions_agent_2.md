# Agent 2 prompt — refinement decision table

**Scope:** Agreement record for [`agent_2_decomposition.md`](agent_2_decomposition.md).  
**Status:** Agreed items **implemented** in `agent_2_decomposition.md` as of this file’s last update.

| ID | Topic | Decision | Detail |
|----|--------|----------|--------|
| R1 | Atomic definition vs compound limit | **Agreed — implemented** (budget **raised to 8**) | **goal = smallest pieces that preserve meaning** + **each piece ≤ compound_operator_limit** (default **8** in `smt/wfm/config/wfm.json`, synced in prompt). Examples fit published counting rule. |
| R2 | Splittability sentence | **Agreed — implemented** | Uses **splittable into independent claims without losing meaning** (aligned with `Agent_WFM.md`). |
| R3 | Operator counting | **Agreed — implemented** | **Plain-language counting rule** plus **micro-examples**; examples of decomposition annotated / chosen to match. |
| R4 | LIMIT_EXCEEDED vs user-facing hint | **Agreed — implemented** (+ structured trace) | **Orchestration-owned** hint line. Model outputs **`LIMIT_EXCEEDED: true`** plus **OFFENDER** section(s): verbatim sub-statement, **OPERATOR_TOTAL** / **OPERATOR_BUDGET**, **OPERATOR_TRACE** (each +1 with rule 1–4), **SUMMARY** — must **not** include the product hint in model output. |
| R5 | Step ordering in INSTRUCTIONS | **Agreed — implemented** | Single **PROCEDURE**: decompose first, **then** count each piece, **then** emit numbered list **or** LIMIT_EXCEEDED. |
| R6 | Single-item success output | **Agreed — implemented** | **SUCCESS OUTPUT** states explicitly that a **one-item** numbered list is valid and spurious splits are wrong. |
| R7 | Input provenance | **Agreed — implemented** | **INPUT** line: plain NL from Agent 1, no metadata. |

---

## Reference (historical): R4 options

`Agent_WFM.md` requires the user to see this exact sentence on limit exceed:

*“Try turning this into several shorter rules and submitting them one at a time.”*

**Chosen approach:** Application code detects `LIMIT_EXCEEDED` and appends that sentence; the model does not emit it.

