# Registry M4 / resolve empirical — what changed (2026-04-09)

This file records **prompt and pipeline** tuning driven by **`m4_warm_eval_v1`** (warm-registry JSONL). It does **not** replace **`REGISTRY_M3_EVAL_DECISIONS.md`** (retrieval Lane A / Protocol B).

## What ran

- **Harness:** `python -m registry_stage.m4_warm_eval --out registry_stage/eval_runs/<name>.jsonl`
- **Fixtures:** `eval_fixtures/m4_warm_seed_bundle.json`, `m4_warm_reuse_bundle.json` (seed session → persist registry → reuse bundle).
- **Index:** BGE+FAISS, `single_concat` + `conservative`, `authoritative_min_score` **0.35** (unchanged from M3 lock).

## Decisions (implemented)

1. **Prompts** (`registry_stage/prompts/`): **gap extract** — anti-fragmentation, substring dedup examples, constant vs sort bias, B-style relation/`function` gaps; **search expand** — whole-entity paraphrases + good/bad examples; **resolve** — fluent `registry_resolved_nl`, no quote-stitching + examples.
2. **Heuristic gaps vs LLM:** When **`enable_llm=True`** and a real **`llm_complete`** is used, **Title-Case heuristic gaps are not merged into `gap_spans`** (`line_driver.py`). Heuristic **remains** when **`enable_llm=False`** (CI / `--no-llm`). **`structured_gaps`** (populate input) were always LLM-only; this change denoises **`gap_spans`** and resolve context without changing populate when structured output is unchanged.

## Numeric guardrails

- **Not tuned in this round.** M4 validator still enforces schema, success predicate, and **`cited_entry_ids`** ⊆ authoritative hits; **no** edit-distance or similarity thresholds were added to code.
- **Still owed (per dev plan inventory):** implement candidate-vs-`statement_nl` checks + calibrate cutoffs on a growing resolve eval set.

## Observations (single-fixture snapshot)

- **Reuse L1:** Resolved NL quality improved substantially vs pre-prompt baseline.
- **Seed L0 `gap_spans`:** Fragment tail (**Meridian**, **Analytics**, etc.) removed after heuristic-off when LLM on; remaining noise is **model** extraction (e.g. extra spans), not regex merge.
- **Reuse L0:** Occasional verb / tail wording variance between runs (model stochasticity); monitor on broader eval.

## Next empirical pass

- Re-run **`m4_warm_eval`** (or expand fixtures) after **any** prompt or `line_driver` change; stamp **header `prompt_sha256`** in JSONL.
- When ready for **numeric M4 guardrails:** add validator code + labels, then sweep cutoffs (document results here or extend this file).
