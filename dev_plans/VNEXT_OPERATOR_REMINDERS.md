# vNext — operator reminders (post-integration)

**Last updated:** integration chunk completing deferred vNext pipeline items.

## Completed in codebase

- Extract accepts **core eight + vNext eight** (`extractor_vnext_addendum.md`, `validate_rule_dict`).
- **`rules_extracted.json` envelope:** `policy_semantics_version` **1.1** + `pivot_ir_extensions: ["vnext_8"]` when expansion rules present (`rules_document.py`).
- **`--no-vnext-lowering`** CLI flag (debug; fails if expansion templates remain).
- **Template generator** context + prompt section for **vNext rule_ids** and assessment linearized excerpt.
- **Deterministic extract NL goldens** (`tests/fixtures/extract_vnext_nl_golden.json`).
- **Template suite vNext smoke** (`template_suite_vnext_suite.json` + 8 scenarios).
- **`SUM_THRESHOLD`:** single cap **4 terms** everywhere (no 8-term schema).

## Reminders — keep on your radar

### 1. Template generator targeting vNext worlds (important)

When running `--with-template-generator`, verify generated `template_suite_generated.json` includes tests that hit **expansion rule_ids** and variables from `K_OF_N` / `SUM_THRESHOLD` / `TABLE_BLOCK` — not only lowered core ids. Re-read `prompts/template_generator.md` § vNext expansion templates.

### 2. Live extract e2e (optional, not default CI)

- Deterministic goldens run in every `pytest`.
- Live LLM extract per template: `PIVOT_RUN_LLM_EXTRACT=1 pytest …/test_extract_vnext_nl_golden.py::test_extract_vnext_k_of_n_live_llm`
- Extend with one test per template kind as extract quality stabilizes.

### 3. `policy_semantics_version` 1.1

- Policies with vNext rules **must** use **1.1** + `pivot_ir_extensions: ["vnext_8"]` in `rules_extracted.json` (auto-written on pipeline extract).
- Hand-edited JSON without envelope will fail `parse_rules_document`.

### 4. `--no-vnext-lowering`

- Use only to debug lowering bugs; production runs should omit this flag.

## Still optional / future polish

- WFM emitting NL that steers extract toward vNext (WFM still outputs lines only).
- Per-template **live** extract regression matrix in CI (cost/latency).
- Template generator **quality gate** asserting min coverage of vNext rule_ids in generated suite.

See [`dev_plan_vnext_pipeline_integration_v1.md`](dev_plan_vnext_pipeline_integration_v1.md) acceptance criteria.
