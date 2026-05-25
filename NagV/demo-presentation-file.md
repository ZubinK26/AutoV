# Pivot pipeline demo — presentation reference

Audience-oriented notes for walking **Scope rewriter → WFM → extract → meta-scheme → Z3 → checks → optional executable tests**.  
**Example run (“scope rewriter 2”):** ADD course grading-style policy, `latest.nl` → full pivot under `scope_rewriter_2_wfm`.

**Related:** [Extract-Pivot.md](Extract-Pivot.md), [pivot_pipeline/ARCHITECTURE.md](pivot_pipeline/ARCHITECTURE.md) (Mermaid diagram), [pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md](pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md).

---

## 1. Pivot **rule templates** (`template_class`) — what they are, expressivity (objective)

Rules are **JSON objects** with exactly one `template_class` from a **fixed list of eight** (validated by Pydantic before compile).

| Template | In simple terms | Logical expressivity (objective) |
|----------|-----------------|----------------------------------|
| **CONSTANT_RELATIONAL** | Variable vs **constant** | Atomic constraints: `EQ`, `NEQ`, `GT`, `LT`, `GTE`, `LTE` with a **yields** outcome (`SATISFIED` / `UNSATISFIED`). |
| **SET_INCLUSION** | Value in / not in a **finite list** | Finite enumeration membership (literal domains). |
| **VARIABLE_RELATIONAL** | Variable vs **variable** | **Relational** comparison between two variables (e.g. `a` `LT` `b`), **not** multiplication; **yields** as in constant form. |
| **ARITHMETIC_EVALUATION** | One linear step, then compare | Single `ADD`/`SUBTRACT`/`MULTIPLY`/`DIVIDE` step vs `target_limit`; **restricted** multiply (no variable×variable as operands in this template only). **Variable×variable products** in policy use **`varprod_cmp`** inside **`LOGICAL_IMPLICATION`** (see row below), not this row. |
| **LOGICAL_IMPLICATION** | If … then … | **ConditionExpr** trees (`and`/`or`/`not`, atoms, comparisons, one **varprod_cmp** per rule where allowed) → material implication between trigger and required side. |
| **PREEMPTION** | Override / bypass | When `preempting_condition` holds, **force** outcome or **bypass** an earlier rule by `target_rule_id` (v1: one target per preemption row). |
| **EXCLUSIVE_CHOICE** | Exactly / at most one | Cardinality on **≥2** choice variables (`exactly_one` or `at_most_one`). |
| **LOGICAL_IFF** | If and only if | Biconditional between two `ConditionExpr` sides. |

**Objective summary:** The IR is **decidable, finite-variable** policy-style logic: propositional structure over **comparisons and bounded linear arithmetic**, plus **finite** sets and **explicit** exceptions—**not** full first-order or temporal logic, **not** unbounded quantification. See [PIVOT_TEMPLATE_SYSTEM.md §5](pivot_pipeline/PIVOT_TEMPLATE_SYSTEM.md).

---

## 2. **Meta-scheme** — how it is made, how it is used, Z3

**Made from:** `rules_extracted.json` (after extract + optional registry). The compiler (`load_rules_and_compile`) parses each rule, runs the **pathway compiler**, and produces **`meta_scheme.json`**.

**What it contains (conceptually):**

- **Policy metadata:** `policy_id`, `policy_semantics_version`, variable sorts, baseline evaluation posture.
- **`rules[]`:** All rules, including **PREEMPTION** rows.
- **`evaluation_pathways[]`:** Each pathway lists **`must_satisfy_all`** (non-preemption rules that must hold **together** on that path) and **`must_not_trigger`**. Preemption rules are **not** dropped from `rules[]`; they are applied in the Z3 layer even when omitted from `must_satisfy_all` (v1 design).

**How it is used:**

1. **Precheck / critics:** Heuristic or LLM compares **NL** (normalized) to **pathways + rule list**.
2. **Z3:** `z3_compile.build_solver(meta)` encodes rules and pathways as **Z3 formulas** (Python API), then `check()` / models for **sat** / **unsat** / **unknown**. Scenario variables come from the policy’s declared sorts (bool/int as implemented).
3. **Back-translation:** `meta_scheme_to_markdown(meta)` builds **`synthetic_en.md`** (compact index: rule ids, templates, scoping, pathways)—not a prose paraphrase of every condition.

**Objective point:** The meta-scheme is the **compiled, structured semantic** object; Z3 is the **automated reasoner** over that encoding.

---

## 3. **Executable test templates** (template suite) — kinds, purpose, workflow

The **template suite** is a **JSON file** (`schema_version: 1`) whose **`instances[]`** entries use **`template_kind`** from a **fixed schema** ([`template_suite/schemas.py`](pivot_pipeline/template_suite/schemas.py)). **Kinds are not invented by the LLM**; only **fields inside** each instance (worlds, queries, goldens) are filled.

| `template_kind` | What it stress-tests (simple) | Why it matters |
|-----------------|--------------------------------|----------------|
| **scenario** | Fix a **world** (variable assignments); expect **SAT** or not. | “Is there any assignment consistent with policy + scenario?” — basic feasibility. |
| **decision_query** | In a world, is a **rule** (or metric) **satisfied** vs golden? | Ground-truth check that the encoded obligation matches intent on a case. |
| **rule_attribution** | Same + **which rule formulas** evaluate true in the witness model vs golden list. | Sensitivity: attribution definition is **engine-defined** (see run reports); goldens must match tool semantics. |
| **boundary** | Sweep one **axis** variable (three values) for a query; compare three decisions. | Threshold / edge behavior (e.g. 29 vs 30 vs 31 lines). |
| **counterfactual_flip** | Two worlds (**base** vs **mutant**); expect flip in sat or decision. | “Changing one fact reverses outcome” — causal sharpness tests. |
| **obligation_inventory** | List **obligations** (pathway `must_satisfy_all`) vs golden list. | Structural completeness vs expected rule set on a path. |
| **sat_unsat** | World + policy should be **sat** or **unsat** as specified. | Explicit consistency / conflict checks. |
| **pairwise** | Two small **deltas** to world; expect **equal** decisions (or not). | Fairness / stability of classification under symmetric tweaks. |

### Generation and execution workflow

1. **Generation (optional LLM):** `--with-template-generator` — Gemini reads **policy context** (excerpts of rules, synthetic, etc.) and produces **`template_suite_generated.json`** validated against **`TemplateSuiteFile`**. Retries on schema failure.
2. **Or file-based:** `--template-suite path/to/suite.json` — no generator; you supply (or reuse) a suite.
3. **Execution:** Each instance is **lowered** to Z3 with the **same** `meta_scheme` / `rules_extracted.json` snapshot; **actual** results are compared to **`golden`** in [`diff.py`](pivot_pipeline/template_suite/diff.py).
4. **Report:** **`template_run_report.json`** — per-instance `pass` / `fail` / `inconclusive` / `error` + summary counts. Failures are often **non-fatal** to the overall run outcome unless you add strict CI flags later.

---

## 4. **Scope rewriter 2** — major intermediate products + **file locations**

Roots (from repo **`AutoV`**):

| Stage | What it is | Example path (this run) |
|-------|------------|-------------------------|
| **Reference / source doc** | Long-form policy Markdown used as rewriter input | `NagV\pivot_pipeline\inputs\scope_rewriter_2_input` |
| **Scope rewriter output — plain rules** | `latest.nl` (one encodable rule per line) | `NagV\exports\scope_rewriter\scope_rewriter_2_run\scope_rewriter\latest.nl` |
| **Scope rewriter sidecar** | Fidelity notes, omissions, model metadata | `NagV\exports\scope_rewriter\scope_rewriter_2_run\scope_rewriter\latest.json` |
| **Rewrite report** | Human-readable rewriter summary | `NagV\exports\scope_rewriter\scope_rewriter_2_run\scope_rewriter\rewrite_report.md` |
| **Rewriter log** | Append-only trace | `NagV\exports\scope_rewriter\scope_rewriter_2_run\scope_rewriter_log.jsonl` |
| **Optional history** | Round snapshots | `NagV\exports\scope_rewriter\scope_rewriter_2_run\scope_rewriter\history\` |
| **Pivot work directory** | Canonical folder for WFM → end | `NagV\exports\pivot_runs\scope_rewriter_2_wfm\` |

**Inside `scope_rewriter_2_wfm` (major artifacts):**

| Artifact | Role |
|----------|------|
| `phase0_normalized_nl.txt` | **WFM-normalized** NL (authoritative text for extract + precheck). |
| `pivot_wfm_phase0_meta.json`, `pivot_wfm_nl_aggregate.json`, `nl_chunk_progress.json` | WFM progress / aggregate metadata. |
| `pivot_wfm_coverage_log.jsonl`, `wfm_handoffs\*.json` | Per-chunk WFM handoffs / coverage log. |
| `extract_rewrite_log.jsonl` | Extract rewrite trace (if used). |
| `phase1_rules_raw.json` | Raw extract before registry (when extract runs). |
| `identifier_registry.json` | Registry pass output (canonical names). |
| `rules_extracted.json` | **Frozen** `{ policy_id, rules[] }` for the run. |
| `rules_source.txt` | Effective NL snapshot written for the run (matches precheck input). |
| `meta_scheme.json` | **Compiled** pathways + rules. |
| `z3_result.json` | Solver status + model excerpt / stats. |
| `synthetic_en.md` | Deterministic markdown summary from meta-scheme. |
| `precheck.json` | Heuristic NL vs model check. |
| `ir_structure_check.json` | Varprod / IR-shape guard output. |
| `critic_report.json`, `critic_result.txt` | Semantic critic JSON + raw LLM output (if critic ran). |
| `template_suite_generated.json` | LLM-authored executable suite (if generator ran). |
| `template_generator_raw.txt` | Raw generator output (audit). |
| `template_run_report.json` | Executable suite verdicts. |
| `run_summary.json` | **One-page** run outcome + key paths. |
| `wfm_rewrite_scratches\` | Optional scratch dirs from interactive WFM repair. |

**Absolute path prefix:** `C:\Users\PC\Documents\Project_Cursor\AutoV\` + relative paths above (adjust if your clone lives elsewhere).

---

## 5. End-to-end demo sentence (elevator pitch)

> We start from a real policy (Markdown or plain rules). **Scope rewriter** can shrink long prose into **encodable lines** with an auditable sidecar. **Pivot WFM** normalizes those lines; **extract** turns them into a **typed JSON IR**; we **compile** a **meta-scheme** and prove **consistency with Z3**; optional **critic / tester / cross-critic** align NL to the model; optional **template suite** runs **real solver scenarios** against **goldens** for regression-style evidence.

---

*File: `NagV/demo-presentation-file.md`*
