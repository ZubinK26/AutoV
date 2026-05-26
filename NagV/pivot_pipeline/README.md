# Pivot policy pipeline

Machine contract for the extracted rule IR: [`NagV/Extract-Pivot.md`](../Extract-Pivot.md).  
Architecture (Mermaid + plain language): [`ARCHITECTURE.md`](ARCHITECTURE.md).  
**Demo / presentation** (templates, meta-scheme, test templates, artifact paths): [`../demo-presentation-file.md`](../demo-presentation-file.md).  
**Template system** (all eight `template_class` values, routing, nesting, scope, reference meta-scheme + NL): [`PIVOT_TEMPLATE_SYSTEM.md`](PIVOT_TEMPLATE_SYSTEM.md).

## Prerequisites

- Install the workspace from the **AutoV repo root**: `pip install -e .`
- **Python 3.11+**
- **`GEMINI_API_KEY`** in `.env` at the repo root (see [`.env.example`](../../.env.example)). Pivot LLM calls use **Gemini** (`pivot_pipeline.llm.pivot_llm_complete`).

## What runs by default

From a natural-language rules file, a typical run:

1. **Phase 0 — Pivot WFM** normalizes the policy text in chunks (unless `--skip-phase0` and a usable `phase0_normalized_nl.txt` already exists in `--work-dir`).
2. **Phase 1 — Extraction** turns lines into structured rule objects (JSON IR), then by default a **registry** pass aligns identifiers across rules (disable with `--skip-registry`).
3. **Compile + Z3**, heuristic **precheck**, then optional stages when you pass flags (**tester** = NL↔linearized per-rule content, semantic critic, cross-critic, template suite, etc.).

You can **reuse** prior extraction by passing **`--rules-json`** pointing at an existing `{ "policy_id": "…", "rules": [ … ] }` file; if that file exists, Phase 1 **skips** the extract LLM. Use **`--no-llm`** only when you intend to forbid LLM calls (extraction will not run without a usable `--rules-json`).

## Commands

Full pipeline (Phase 0 + Phase 1 LLM when no `--rules-json`):

```bash
pivot-pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/my_run
```

Same, using the package module:

```bash
python -m pivot_pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/my_run
```

**Pre-WFM — Scope Rewriter** (optional: reference doc → plain `latest.nl` + `latest.json` before Phase 0):

```bash
scope-rewriter --reference path/to/reference.md --work-dir exports/scope_rewriter/my_run
python -m pivot_pipeline.scope_rewriter_cli --reference path/to/reference.md --work-dir exports/scope_rewriter/my_run --non-interactive
```

If `scope-rewriter` is missing (editable install not refreshed), from the **AutoV** repo root run the script directly (no `PYTHONPATH` needed):

```bash
python NagV/pivot_pipeline/scope_rewriter_cli.py --reference path/to/reference.md --work-dir exports/scope_rewriter/my_run
```

Skip WFM (uses `work-dir/phase0_normalized_nl.txt` if present and non-empty; otherwise raw `--input`):

```bash
python -m pivot_pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/my_run --skip-phase0
```

Replay from existing extracted JSON:

```bash
pivot-pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/my_run --rules-json path/to/rules_extracted.json
```

Stop after extraction (writes `rules_extracted.json`):

```bash
pivot-pipeline --input path/to/rules.nl --work-dir exports/pivot_runs/extract_only --extract-only
```

**Further options:** `pivot-pipeline --help` (e.g. `--with-critic`, `--with-cross-critic`, `--with-cross-repair`, `--with-tester`, `--with-test-repair`, `--interactive-tester`, `pivot-tester` for replay on existing work dirs, `--with-template-generator`, `--template-suite`, `--no-vnext-lowering`, `--repairer-max-rounds`, interactive modes).

### vNext expansion templates

Eight optional `template_class` values (`K_OF_N`, `SUM_THRESHOLD`, …) may appear in `rules_extracted.json`. They are **lowered to core IR** before Z3 unless `--no-vnext-lowering` is set. Policies with expansion rules use **`policy_semantics_version`: `"1.1"`** and **`pivot_ir_extensions`: `["vnext_8"]`**. `SUM_THRESHOLD` allows **at most 4** terms. See [`PIVOT_TEMPLATE_SYSTEM.md`](PIVOT_TEMPLATE_SYSTEM.md) and [`dev_plans/VNEXT_OPERATOR_REMINDERS.md`](../../dev_plans/VNEXT_OPERATOR_REMINDERS.md).

`run_summary.json` may include: `vnext_lowering`, `policy_semantics_version`, `pivot_ir_extensions`, `assessment_linearized`, `expansion_assessment_digest`.

**Template suite (vNext smoke):** `pytest` includes `test_template_suite_vnext.py`; fixture suite `tests/fixtures/template_suite_vnext_suite.json` with `extract_vnext_golden_rules.json`.

## Fixtures and tests

- Minimal rules fixture: [`tests/fixtures/minimal_rules.json`](tests/fixtures/minimal_rules.json)
- Tests live under [`tests/`](tests/); run **`pytest`** from the **repo root** (see root `README.md`).

## Related paths

- WFM profile assets: **`NagV/pivot_wfm/`** (`wfm_profile=pivot`).
