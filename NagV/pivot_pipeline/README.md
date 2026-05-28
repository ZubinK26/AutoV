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

**Further options:** `pivot-pipeline --help` (e.g. `--with-critic`, `--with-cross-critic`, `--with-cross-repair`, `--with-tester`, `--with-test-repair`, `--interactive-tester`, `--resume-tester-repair`, `pivot-tester` / `pivot-test-repair` on existing work dirs, `PIVOT_TESTER_REPAIR_COMPILE_ATTEMPTS` default 5, `--with-template-generator`, `--template-suite`, `--no-vnext-lowering`, `--repairer-max-rounds`, interactive modes).

**Semantic critic DRIFT repair:** After DRIFT, **critic triage** (`y` / disagree numbers, `retriage`) like CrossCritic. Each `REPAIR` runs **focused** Repairer_Piv (stubs + server merge) with up to `PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS` (default **5**) Repairer_Piv calls; **registry** retries are separate (`PIVOT_CRITIC_SEMANTIC_REPAIR_REGISTRY_ATTEMPTS`, default **3**) and do not re-invoke Repairer_Piv. Order: Repairer → pre-compile → registry (with JSON repair / slug-unchanged skip) → artifacts. **`PIVOT_CRITIC_SEMANTIC_REPAIR_MAX=0`** (default) = unlimited user `REPAIR` sessions. Repeated identical errors trigger **stall detection** (`PIVOT_SEMANTIC_REPAIR_STALL_THRESHOLD`). Cross-rule findings route to **cross_coherence** / CrossRepairer unless `PIVOT_CRITIC_SEMANTIC_REPAIR_ALLOW_CROSS_FINDINGS=1`.

**CrossCritic triage:** With `--with-cross-critic`, `--with-cross-repair`, and `--interactive-cross-coherence` (or `--interactive-policy`), findings are numbered; you accept all (`y`) or enter disagree indices (`2,3`). Only approved findings go to CrossRepairer (`cross_repair_handoff.json`). Type `retriage` at the gate to re-prompt. Each `REPAIR` you type is allowed without a round cap by default (`PIVOT_CROSS_REPAIR_MAX_ROUNDS=0`); set a positive value to limit sessions.

**CrossCritic JSON repair:** Malformed critic JSON triggers up to `PIVOT_CROSS_CRITIC_JSON_REPAIR_MAX` (default 3) repair calls; bare `findings` arrays are wrapped automatically. In interactive mode, type `retry` if parsing still fails.

**CrossRepairer hardening:** Focus-rule stubs + server merge, shared `repairer_ir_normative.md` + `cross_repairer_ir_addendum.md` (forbids nesting `k_of_n` inside `LOGICAL_IMPLICATION` triggers; wire aggregates with `atom` booleans or `K_OF_N` **`result_variable`**), **post-merge IR validation** (`repair_ir_validation.py`: rejects silent no-ops, illegal `variable`/`yields` on `K_OF_N`, logs `sanitize_dropped_keys` in `cross_repairer_trace.jsonl`), pre-compile before registry, compile/merge error feedback (including `k_of_n` recovery hint on retry), registry JSON repair (`PIVOT_REGISTRY_JSON_REPAIR_MAX`) and slug-unchanged skip. Assessment linearization shows `assigns result → …` or `no result_variable` per `K_OF_N`. Env: `PIVOT_CROSS_REPAIR_COMPILE_ATTEMPTS` (default 5), `PIVOT_CROSS_REPAIR_REGISTRY_ATTEMPTS` (default 3), `PIVOT_CROSS_REPAIR_SKIP_REGISTRY`, `PIVOT_CROSS_CRITIC_API_AUTO_RETRIES` and `PIVOT_CRITIC_API_AUTO_RETRIES` (default **0** = unlimited automatic retry on 503 in interactive mode; post-repair semantic critic is skipped when `--skip-semantic-critic`).

### Phase 0 WFM — omit OUT_OF_SCOPE lines (interactive)

Downstream phases use **`work-dir/phase0_normalized_nl.txt`**, not scope-rewriter `latest.nl`. For recruitment-scale runs, pass **`--interactive-policy`** so Phase 0 can drop rules instead of failing coverage.

At each chunk, when prompted `Accept entire confirmation package…? [Y/n/o]`:

| Key | Action |
|-----|--------|
| **Y** | Accept Agent 3 as-is (OUT_OF_SCOPE lines will fail coverage) |
| **n** | Disagree → comment → optional **confirm omit** → Agent 4 → pass 2 |
| **o** | Omit chunk line numbers from the in-run policy and **retry the chunk** (no handoff for that attempt) |

After omit/drop, the run writes **`pivot_wfm_effective_source.nl`** and **`pivot_wfm_dropped_rules.jsonl`**. Resume the same `--work-dir` without `--reset-progress` when those files exist. If coverage still fails after retries, the **`[d]` drop** menu applies (same drop machinery).

See [`dev_plans/dev_plan_pivot_wfm_interactive_omit_v1.md`](../../dev_plans/dev_plan_pivot_wfm_interactive_omit_v1.md).

### vNext expansion templates

Eight optional `template_class` values (`K_OF_N`, `SUM_THRESHOLD`, …) may appear in `rules_extracted.json`. They are **lowered to core IR** before Z3 unless `--no-vnext-lowering` is set. Policies with expansion rules use **`policy_semantics_version`: `"1.1"`** and **`pivot_ir_extensions`: `["vnext_8"]`**. `SUM_THRESHOLD` allows **at most 4** terms. See [`PIVOT_TEMPLATE_SYSTEM.md`](PIVOT_TEMPLATE_SYSTEM.md) and [`dev_plans/VNEXT_OPERATOR_REMINDERS.md`](../../dev_plans/VNEXT_OPERATOR_REMINDERS.md).

`run_summary.json` may include: `vnext_lowering`, `policy_semantics_version`, `pivot_ir_extensions`, `assessment_linearized`, `expansion_assessment_digest`.

**Template suite (vNext smoke):** `pytest` includes `test_template_suite_vnext.py`; fixture suite `tests/fixtures/template_suite_vnext_suite.json` with `extract_vnext_golden_rules.json`.

## Fixtures and tests

- Minimal rules fixture: [`tests/fixtures/minimal_rules.json`](tests/fixtures/minimal_rules.json)
- Tests live under [`tests/`](tests/); run **`pytest`** from the **repo root** (see root `README.md`).

## Related paths

- WFM profile assets: **`NagV/pivot_wfm/`** (`wfm_profile=pivot`).
