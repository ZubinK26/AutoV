# Dev plan: CrossCritic + CrossRepairer (post-pipeline IR coherence)

## Names

- **CrossCritic** — LLM pass that audits **cross-rule encoding coherence** using **processed NL** + **linearized model** (human-readable), not NL-vs-synthetic wording parity (that stays **`pivot_critic`**).
- **CrossRepairer** — LLM pass that returns **patched `rules`** (+ `change_summary`) from a **CrossCritic handoff**, same mechanical apply path as Repairer_Piv (validate → optional registry → compile → write artifacts).

## Problem

Per-line extract + registry unify **aliases**, not **global modeling choices**. Example: multiple English “denied” obligations formalized with **different consequent variables** (`decision` vs `request_is_denied`) under the **same** `LOGICAL_IMPLICATION` template. That is hard for **invariant templates**, **outcome slots**, and **review**; it is **visible** when **processed NL** and a faithful **linearized rule list** are shown together.

## Goals

1. After the **existing** pivot run has produced a **`rules_extracted.json`** (and semantic critic has completed per current product choice), optionally run **CrossCritic** on:
   - **processed NL** = `work_dir/phase0_normalized_nl.txt` (or `nl_after_extract_rewrites.txt` when that is the effective NL artifact — **same resolution rule as `run.py`** for `nl_text_for_artifacts` / precheck source), and  
   - **linearized model** = deterministic **string built from `rules_extracted.json`** (one line per rule; variable names and template class surfaced — same spirit as `exports/.../linearized_nl_and_model.txt` model section).
2. Persist **structured report** (e.g. `cross_critic_report.json` + raw `cross_critic_result.txt`).
3. Optionally run **CrossRepairer** (interactive or bounded rounds) to apply fixes; reuse **shared apply core** with Repairer_Piv (`parse_json_object` + `RepairerPivOutput`-shape or dedicated Pydantic model mirroring it).
4. After successful repair + compile + Z3 smoke: **re-run `pivot_critic`** (semantic critic) on **effective NL + fresh `synthetic_en.md`** so **NL alignment** is re-checked (user requirement).
5. **CLI** so an existing `work_dir` can be processed without re-extract: e.g.  
   `python -m pivot_pipeline --work-dir <PATH> --input <same as run> --skip-phase0 --rules-json <work_dir>/rules_extracted.json --cross-coherence ...`  
   (exact flags in Implementation; may be `--with-cross-critic`, `--with-cross-repair`, `--interactive-cross-coherence` mirror of critic REPAIR).

## Non-goals (v1)

- **Z3 invariant queries** (separate track).
- Changing **registry** semantics to merge non-alias outcome variables without explicit repair intent.
- Replacing **`pivot_critic`** — CrossCritic is **orthogonal** (IR coherence vs effective NL ↔ synthetic).

## Design

### A. Deterministic linearization module

- New helper e.g. `pivot_pipeline/linearize_rules.py`: `linearize_rules_for_cross_critic(rules: list[dict]) -> str`  
  - One line per rule: `rule_id`, `template_class`, compact consequent/antecedent **with variable names preserved** (reuse conventions from `linearized_nl_and_model.txt`).  
  - **No LLM**; unit-tested golden strings on a small fixture.

### B. CrossCritic

- **Prompt** `prompts/cross_critic.md`: instruct focus on **cross-rule coherence** — split outcome channels, duplicated obligation patterns, inconsistent denial/permit slots, PREEMPTION vs obligation mismatches **visible** from linearization + NL; **do not** re-litigate benign NL paraphrase (defer to `pivot_critic` for NL↔synthetic doc drift).
- **Output** JSON (strict), analogous to `CriticReport`: `verdict` e.g. `PASS` | `ISSUES`, `findings[]` with `id`, `severity`, `category` (e.g. `outcome_split`, `preemption`, `inconsistency`, `other`), `rule_ids`, `explanation`, optional `recommendation`.
- **Agent module** e.g. `cross_critic_agent.py`: `run_cross_critic(processed_nl: str, linearized: str) -> (raw, report)`.

### C. CrossRepairer

- **Prompt** `prompts/cross_repairer.md`: input = **handoff** from CrossCritic findings + **current rules** (full JSON array) + short **policy_id**; output = `{ "rules", "change_summary" }` only; **normative IR shape** reuse bullets from `repairer_piv_semantic.md` / structural (single `target_rule_id`, etc.).
- **Module** e.g. `cross_repairer_agent.py`: call shared **`_llm_repairer_output`-style** JSON parse retry if Repairer stack is refactored; else duplicate minimal retry from `repairer_piv_agent.py` until shared core exists.
- **Apply path**: same as semantic repair in `run.py` — registry optional, `load_rules_and_compile`, write `rules_extracted.json`, `meta_scheme.json`, `z3_result.json`, `synthetic_en.md`, precheck; append **`cross_repairer_trace.jsonl`**.

### D. Orchestration

- **When**: only after **main pipeline** has finished through **semantic critic loop** (policy: **require `critic_passed`** before CrossCritic, or allow `--cross-coherence-skip-critic-gate` for dev — default **strict**).
- **Order**:
  1. Build `linearized` from `rules_extracted.json`.
  2. Load processed NL from agreed path.
  3. **CrossCritic** → save reports.
  4. If `ISSUES` and `--interactive-cross-coherence`: prompt **REPAIR** / **SKIP** / abort (mirror critic gate).
  5. **CrossRepairer** on REPAIR → apply rules → compile → Z3 → synthetic → precheck.
  6. **Re-run `run_pivot_critic_parsed(effective_nl, synth)`** once (or small loop if needed); write updated `critic_report.json` / `critic_result.txt`; if DRIFT, surface **existing** policy gate behavior (user abort / PROCEED / semantic Repairer — **do not** auto-loop CrossRepairer in v1 without product decision).
- **Work dir artifacts**:  
  `cross_critic_report.json`, `cross_critic_result.txt`, optional `cross_repairer_trace.jsonl`, `rules_after_cross_repair.json` (if distinct from semantic repair filename).

### E. CLI

Extend `cli.py` / `run_pivot_pipeline` kwargs e.g.:

- `--with-cross-critic` — run CrossCritic after successful semantic critic path.
- `--with-cross-repair` — allow CrossRepairer when interactive and CrossCritic reports ISSUES (requires `--interactive-policy` or new `--interactive-cross-coherence`).
- Optional: **`python -m pivot_pipeline.cross_coherence`** thin entry that **requires** existing `work_dir` + `rules_extracted.json` + NL file — for “run only this segment.”

Document example in plan body:

```text
cd NagV
python -m pivot_pipeline --input pivot_pipeline/golden_test_run/input/Test_input2.md ^
  --work-dir exports/pivot_runs_test_input2 --skip-phase0 ^
  --rules-json exports/pivot_runs_test_input2/rules_extracted.json ^
  --with-critic --with-cross-critic --interactive-policy
```

(Exact combination after implementation; `--with-cross-critic` may imply re-run from compile only if wired as a **post step** inside `run_pivot_pipeline` after first critic success.)

### F. Tests

- `test_linearize_rules.py` — snapshot / assert key lines contain `decision` vs `request_is_denied` for fixture.
- `test_cross_critic_agent.py` — mock LLM JSON, parse report.
- `test_cross_repairer_agent.py` — mock LLM, validate output rules shape.
- Integration (optional): temp `work_dir` with mini `rules_extracted.json` + NL file, run orchestration function with mocks.

### G. Risks

- CrossCritic **false positives** → noise; mitigate with categories + severity + human skip.
- CrossRepair **semantic drift** → mitigated by **mandatory post Cross-repair `pivot_critic`** pass.
- **Token size** at 100s of rules → truncate linearized with rule id index + excerpt, or summarize via deterministic digest + LLM (future).

## Status

**Implemented** — `linearize_rules.py`, `cross_critic_agent.py`, `cross_repairer_agent.py`, `semantic_critic_loop.py`, `cross_coherence.py` entry, CLI flags on `pivot_pipeline`, orchestration in `run.py`, tests under `pivot_pipeline/tests/`.

---

## Proposed workflow (post-dev, simple language)

1. You run the **normal pivot pipeline** through WFM, extract, registry, Z3, and the **semantic critic** until you’re happy with **English vs synthetic summary** (`pivot_critic`).
2. **CrossCritic** reads **the same processed NL** the pipeline used and a **plain-English line-per-rule dump** of the **current** IR (built in code, no hand editing).
3. It looks for **“whole policy” shape problems** — for example the same idea (like “denied”) showing up as **different variables** in different rules, or other cross-rule weirdness that wouldn’t be caught by comparing NL to the short synthetic doc alone.
4. If it reports **issues**, you can invoke **CrossRepairer** (with prompts/gates similar to today’s repair loop). It proposes **updated rule JSON**; the pipeline **checks** it, **recompiles**, **re-runs Z3**, and **refreshes** the synthetic summary.
5. The pipeline then runs the **semantic critic again** on **fresh synthetic vs NL**, so you know the **coherence fix didn’t break the meaning** you already approved.
6. You keep **`rules_extracted.json`** and reports in **`work_dir`** for audit.

That’s the new “**cross coherence** slice”: **CrossCritic → optional CrossRepairer → mechanical apply → semantic critic sanity check**.
