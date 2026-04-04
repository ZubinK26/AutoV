# WFM prompts

One file per internal agent. Each `agent_*.md` file contains the instruction block to load into your LLM layer.

| File | Agent |
|------|--------|
| [agent_1_completeness_ambiguity.md](agent_1_completeness_ambiguity.md) | Completeness and ambiguity resolution |
| [agent_2_decomposition.md](agent_2_decomposition.md) | Decomposition |
| [agent_3_scope_rewrite.md](agent_3_scope_rewrite.md) | Scope check and rewrite |
| [agent_4_user_presentation.md](agent_4_user_presentation.md) | User presentation and feedback |

## Maintenance notes

- Agent 1's completeness and ambiguity lists are **living documents** — add new types when real user inputs expose gaps.
- Agent 2's decomposition counterexamples are critical; the dominant failure mode is **over-splitting** conditionals. Keep that emphasis when editing.
- Agent 3 carries the formalization scope definition. If pipeline scope changes (**`pipeline_spec.md`**), update this prompt in lockstep.
- Agent 4 is intentionally short. Avoid piling on instructions to preserve conversational quality; keep constraints few and firm.

See **`../Agent_WFM.md`** for WFM control flow and how these prompts fit the module.
