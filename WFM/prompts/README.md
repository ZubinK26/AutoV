# WFM prompts

One file per internal agent. Each `agent_*.md` file contains the instruction block to load into your LLM layer.

| File | Agent |
|------|--------|
| [agent_1_completeness_ambiguity.md](agent_1_completeness_ambiguity.md) | Completeness and ambiguity resolution |
| [agent_2_decomposition.md](agent_2_decomposition.md) | Decomposition |
| [agent_3_scope_rewrite.md](agent_3_scope_rewrite.md) | Scope check and rewrite |
| [agent_4_user_interaction.md](agent_4_user_interaction.md) | User presentation and feedback |

## Maintenance notes

- Agent 1's completeness and ambiguity lists are **living documents** — add new types when real user inputs expose gaps.
- Agent 2's decomposition counterexamples are critical; the dominant failure mode is **over-splitting** conditionals. Keep that emphasis when editing.
- Agent 3 carries the **ClinCon-safe ASP** formalization scope (see **`docs/pipeline_wfm_to_asp.md` §2** and **`pipeline_spec.md`** ClinCon note). If that scope changes, update this prompt in lockstep. **Output lines** are **machine-pinned** (`PASS|REWRITE|OUT_OF_SCOPE: N. "…"`) so merge preview and orchestration can parse reliably — keep that contract when editing. **OUT_OF_SCOPE** `REPORT:` lines should start with a **violation tag** (e.g. `unbounded domain:`) when applicable — see Agent 3 prompt.
- Agent 4 carries **user-facing** tone rules plus **`WFM_PATCH`** machine contract; when editing, keep jargon out of user-visible guidance but preserve parsing rules orchestration relies on.

See **`../Agent_WFM.md`** for WFM control flow and how these prompts fit the module.
