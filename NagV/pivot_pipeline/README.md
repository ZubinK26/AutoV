# Pivot policy pipeline

Machine contract: [`NagV/Extract-Pivot.md`](../Extract-Pivot.md).

## Run (after `pip install -e .` from repo root)

Phase 0 (pivot WFM, needs `GEMINI_API_KEY`) + later phases need Phase 1 JSON today:

```bash
pivot-pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/my_run --rules-json path/to/rules.json
```

Skip WFM (use raw NL only for precheck path):

```bash
python -m pivot_pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/my_run --skip-phase0 --rules-json path/to/rules.json
```

Phase 1 LLM extraction + identifier registry + LLM critic are **stubs** in this snapshot; supply **`--rules-json`** with `{ "policy_id": "…", "rules": [ … ] }` (see `tests/fixtures/minimal_rules.json`).

Phase 0 assets live in **`NagV/pivot_wfm/`** (`wfm_profile=pivot`).
