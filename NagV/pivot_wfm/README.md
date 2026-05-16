# Pivot WFM (Phase 0)

Forked **layout** from `smt/wfm`: prompts live in `pivot_wfm/prompts/`, config in `config/wfm.json`.

Pivot runs pass ``wfm_profile="pivot"`` into :func:`wfm_orchestration.orchestrator.run_wfm_registry_e2e`, which calls ``load_wfm_prompts(wfm_profile="pivot")`` to **append** ``prompts/agent_2_pivot_chunk_cardinality.md`` to the shared Agent 2 system prompt from ``WFM/prompts/``.

Edit files here only — do **not** change `smt/wfm/` for pivot-only prompt tweaks.
