# AutoV / NagV policy pipeline — full workflow guide (for visualization)

**Audience:** Someone who has never opened this repository.  
**Purpose:** Describe every major stage from raw policy text through formalization, alignment checks, template tests, and **external evidence testing** — with a **single small recruitment-style policy** carried through each stage so you can see how the *shape* of the data changes.

**How to use this file:** Each transforming stage uses the same **BEFORE → AFTER → Δ** block plus a **metrics table** and **★ magnitude** score. Paste those onto diagram arrows so viewers see *how much* the representation changes, not just stage names. Suggested diagram prompts are at the end.

**Related docs (deeper detail):** [`ARCHITECTURE.md`](ARCHITECTURE.md), [`diagrams/pipeline_e2e_overview.md`](diagrams/pipeline_e2e_overview.md), [`README.md`](README.md), [`PIVOT_TEMPLATE_SYSTEM.md`](PIVOT_TEMPLATE_SYSTEM.md).

---

## Mental model in one paragraph

Humans write **plain-English rules**. Optional tools **reshape** that text into one-rule-per-line form, then **normalize** it in chunks (Pivot WFM). An **extractor** turns each line into **JSON rules**; a **registry** aligns variable names. A **compiler** builds a **meta-scheme** (policy structure + pathways) and a **Z3** model to check internal consistency. Optional **LLM reviewers** compare English to the formal model (tester, semantic critic, cross-critic) with optional **repair loops**. A **template suite** runs executable micro-scenarios against the same model. Finally, the **external / policy-case tester** reads unstructured evidence (e.g. a CV), builds a **partial world**, and asks whether the person **could** satisfy the policy under strict or lenient assumptions — with **tiered** checks so missing evidence does not masquerade as “incompatible.”

---

## Running example policy (“Mini-BE8”)

Eight lines, same *family* as `inputs/Backend_Engineer2.md` but written here once so every stage below refers to the same story.

| Line | Meaning (informal) |
|------|-------------------|
| 1 | At least 2 years professional backend experience |
| 2 | Professional experience with ≥1 language: Python, Java, Go, C#, JavaScript, TypeScript |
| 3 | Experience with ≥1 API style: REST, GraphQL, or internal service APIs |
| 4 | Experience with ≥1 relational DB (PostgreSQL, MySQL, SQL Server, similar) |
| 5 | Comfortable using Git in a team workflow |
| 6 | Experience with ≥2 of: automated tests, production debugging, cloud, jobs/queues |
| 7 | Worked on a team using code review, PRs, or issue tracking |
| 8 | Can explain technical decisions clearly in written English |

Throughout this doc, **Mini-BE8** is the thread. Examples are grounded in real runs (`Backend_Engineer2.md` → `Backend_Engineer2_v1_wfm`) where noted; JSON may be trimmed for readability.

---

## Diagram convention — every transforming stage

Use the same block on each arrow in your diagram. **Validation-only** stages (precheck, critics) add a **report layer** on top of unchanged IR; they still get BEFORE/AFTER so the diagram shows *new artifact types*, not “no op.”

| Field | Meaning |
|--------|---------|
| **Edge label** | Short phrase for the arrow (copy onto diagram) |
| **Magnitude ★1–5** | How visibly the *representation* changes (not “importance”) |
| **Metrics** | Counts that should jump out in a viz (lines, variables, nesting) |
| **BEFORE** | What enters the stage |
| **AFTER** | What leaves the stage |
| **Δ (delta bullets)** | 3–6 bullets — **put these on the diagram** as annotations |

**Mini-BE8 ladder (representation only):**

| Stage | BEFORE (in) | AFTER (out) | Magnitude | What visibly changes |
|-------|-------------|-------------|-----------|----------------------|
| 0 Scope | 1 Markdown doc, bullets, “You…” | 8 imperative NL lines | ★★★★★ | Document → rule lines; deontic mood; explicit k-of-n |
| 1 WFM | 8 informal lines | 8 audited, numbered rules | ★★★☆☆ | Uniform “Every candidate must…”; split nested ORs; chunk audit trail |
| 2 Extract | 8 English lines | 8 JSON rules + ~30–40 variables | ★★★★★ | Text → typed logic trees; `is_candidate` gate on every rule |
| 3 Registry | Per-rule ad-hoc names | Canonical ids + alias map | ★★★☆☆ | Same JSON shape; vocabulary merged across rules |
| 4 Compile | Flat rule list | Pathway + compiled meta-scheme | ★★★★☆ | Global AND pathway; solver-ready rule bodies |
| 5 Z3 | Meta-scheme (static) | SAT verdict + English back-translate | ★★★☆☆ | “Does this policy hang together?” + `synthetic_en.md` |
| 5b Linearize | JSON IR | Per-rule math-ish English lines | ★★★☆☆ | Same semantics, new *human audit* surface |
| 6 Precheck | NL + model | Heuristic report | ★★☆☆☆ | Pass/fail overlay; no IR rewrite |
| 7–9 Alignment | NL + linearized / synthetic | Finding reports (+ optional IR patch) | ★★☆☆☆ | Evidence of drift; optional repair rewires IR |
| 12 Templates | Meta-scheme | Executable scenarios + Z3 runs | ★★★★☆ | Policy → concrete worlds + golden SAT/UNSAT |
| 13–14 External | Unstructured CV (~40 lines prose) | Partial world JSON + tier verdicts | ★★★★★ | Prose → 20+ typed slots; provenance; block vs compatible |

---

## Stage map (nothing major omitted)

| # | Stage | CLI / entry | Required? | Main outputs |
|---|--------|-------------|-----------|--------------|
| 0 | **Scope rewriter** | `scope-rewriter` / `scope_rewriter_cli` | Optional | `latest.nl`, `latest.json`, history |
| 1 | **Pivot WFM (Phase 0)** | `pivot-pipeline` default | Default on (`--skip-phase0` to bypass) | `phase0_normalized_nl.txt`, WFM handoffs, progress |
| 2 | **Extraction (Phase 1)** | same | Yes (unless `--rules-json` replay) | `rules_extracted.json` |
| 3 | **Registry pass** | same (default) | Default on (`--skip-registry` off) | Updated rules + `identifier_registry.json` |
| 3b | **vNext lowering** | compile path | Automatic unless `--no-vnext-lowering` | Core IR in memory; assessment views keep pre-lowering |
| 4 | **Compile + meta-scheme** | same | Yes (unless `--extract-only`) | `meta_scheme.json` |
| 4b | **Structural repair** | on compile failure | Conditional | `rules_after_semantic_repair.json`, repair traces |
| 5 | **Z3 consistency check** | same | Yes | `z3_result.json` |
| 5b | **Assessment artifacts** | with tester/critic/cross | When those run | `linearized_model_for_assessment.txt`, `synthetic_en.md` |
| 6 | **Precheck** | same | Yes | `precheck.json` |
| 7 | **Tester** | `--with-tester` | Optional | `tester_report.json` |
| 7b | **Test-repair** | `--with-test-repair` + interactive | Optional | Patched rules, traces |
| 8 | **Semantic critic** | `--with-critic` | Optional | `critic_report.json`, `critic_result.txt` |
| 8b | **Semantic repair (Repairer_Piv)** | interactive DRIFT | Optional | `rules_after_semantic_repair.json` |
| 9 | **Cross-critic** | `--with-cross-critic` | Optional | `cross_critic_report.json`, linearized cross view |
| 9b | **Cross-repair** | `--with-cross-repair` | Optional | `cross_repair_handoff.json`, patched rules |
| 10 | **Post–cross semantic pass** | after cross succeeds | When cross ran | Re-run critic alignment |
| 11 | **IR structure / varprod guard** | env flags | Can block | `ir_structure_check.json` |
| 12 | **Template suite** | `--with-template-generator` or `--template-suite` | Optional | `template_suite_generated.json`, `template_run_report.json` |
| 12b | **Template repair** | `--with-template-repair` | Optional | Diagnostic + repaired rules |
| 13 | **External tester (legacy fill + scenario)** | `--with-external-tester` on CLI | Optional | `external_tester_*.json`, world fill logs |
| 14 | **Policy-case pipeline (v4 + tiers)** | `python -m pivot_pipeline.external_tester.run` | Standalone / post-formalization | `policy_case_*.json`, narrative |

Stages **7–12** need a successful **compile + Z3** path (stage 4–5) unless you only replay `--rules-json` into a work dir that already compiled.

---

## Stage 0 — Scope rewriter (optional, pre-WFM)

**What happens:** A long Markdown job spec (headings, bullets, prose) is rewritten into **atomic, encodable lines** — one requirement per line — while a JSON **sidecar** records fidelity (what was merged, paraphrased, or flagged).

**Edge label:** `Unstructured job spec → Encodable rule lines`  
**Magnitude:** ★★★★★ (largest *text* reshape before formalization)

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Container | 1 Markdown file | 1 plain-text `.nl` file | format change |
| Rule lines | 0 (embedded in prose) | 8 explicit lines | **+8 atomic obligations** |
| Voice | 2nd person (“You have…”) | Deontic (“Candidate must…”) | auditable normative form |
| Lists in prose | Inline commas / bullets | `at least one of:` / `at least two of:` | logic-ready enumerations |
| Machine fields | none | sidecar JSON + rewrite log | traceability |

#### BEFORE — `reference.md` (excerpt; typical author input)

```markdown
# Backend Engineer — Job Requirements

We're hiring a backend engineer. You should be a strong fit if most of the below apply.

## Experience
- **2+ years** professional backend engineering
- Professional use of **at least one** of: Python, Java, Go, C#, JavaScript, TypeScript

## Technical skills
- Built or maintained **REST**, **GraphQL**, or internal service APIs
- Used **PostgreSQL**, MySQL, or SQL Server in anger
- Comfortable with **Git** on a team (PRs, shared branches)

## Plus (not all required but valued)
- Automated tests, prod debugging, cloud, queues/cron jobs — **we want depth in at least two areas**
- Team practices: code review, PRs, Jira/Linear
- Clear **written English** for design docs and incident write-ups
```

#### AFTER — `scope_rewriter/latest.nl` (full Mini-BE8 policy)

```text
Professional backend engineering experience must be at least 2 years.
Candidate must have professional experience with at least one of: Python, Java, Go, C#, JavaScript, TypeScript.
Candidate must have experience building, maintaining, or integrating at least one of: REST APIs, GraphQL APIs, internal service APIs.
Candidate must have experience with at least one relational database: PostgreSQL, MySQL, SQL Server, or similar.
Candidate must be comfortable using Git in a team development workflow.
Candidate must have experience with at least two of: automated tests, debugging production issues, cloud infrastructure, background jobs, queues, scheduled tasks.
Candidate must have worked in a software team that uses at least one of: code review, pull requests, issue tracking, or similar engineering practices.
Candidate must be able to explain technical decisions clearly in written English.
```

#### Δ — annotate on diagram

- Removed headings, marketing tone, and “plus” section → **flat numbered obligations**
- Turned bullet soup into **one line per requirement**
- Made **k-of-2** on line 6 explicit (was buried in “depth in at least two areas”)
- Sidecar records merges/paraphrases for human audit

**Command:** `scope_rewriter_cli.py --reference reference.md --work-dir exports/scope_rewriter/my_run`

---

## Stage 1 — Pivot WFM (Phase 0)

**What happens:** The `--input` NL file is processed **in chunks** through a fixed multi-agent workflow: clarify wording, enforce scope, decompose nested ORs, confirm coverage. Progress is resumable.

**Edge label:** `Informal lines → Audited policy text`  
**Magnitude:** ★★★☆☆ (same line count; **syntax and audit surface** change a lot)

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Lines | 8 | 8 | count stable |
| Prefix style | Mixed (“Professional…”, “Candidate must…”) | Uniform **“Every candidate must…”** | one voice |
| Line 3 (APIs) | Single clause | **Nested** action × API type | decomposition |
| Line 6 (skills) | “at least two of” (scope) | May become “at least one of” if WFM softens — **check `phase0`** | auditable change |
| Numbering | None | Optional `1.`…`8.` in some runs | chunk alignment |
| Extra artifacts | 0 | handoffs per chunk, coverage log | **multi-agent trail** |

*Example below uses real `Backend_Engineer2.md` → `phase0_normalized_nl.txt` (direct pivot input, no scope rewriter).*

#### BEFORE — `inputs/Backend_Engineer2.md` (author / product file)

```text
Backend Engineer Job Requirements

You have 2+ years of professional backend engineering experience.

You have professional experience with at least one backend programming language such as Python, Java, Go, C#, JavaScript, or TypeScript.

You have experience building, maintaining, or integrating REST APIs, GraphQL APIs, or internal service APIs.

You have experience working with relational databases such as PostgreSQL, MySQL, SQL Server, or similar.

You are comfortable using Git in a team development workflow.

You have experience writing automated tests, debugging production issues, working with cloud infrastructure, or building background jobs, queues, or scheduled tasks.

You have worked in a software team that uses code review, pull requests, issue tracking, or similar engineering practices.

You can explain technical decisions clearly in written English.
```

#### AFTER — `phase0_normalized_nl.txt` (authoritative for extract)

```text
Every candidate must have at least 2 years of professional backend engineering experience.

Every candidate must have professional experience with at least one of the following: Python, Java, Go, C#, JavaScript, or TypeScript.

Every candidate must have experience in at least one of the following actions: building, maintaining, or integrating; for at least one of the following: REST APIs, GraphQL APIs, or internal service APIs.

Every candidate must have experience with at least one of the following: PostgreSQL, MySQL, or SQL Server.

Every candidate must have experience using Git in team development.

Every candidate must have experience with at least one of the following: automated tests, debugging production issues, cloud infrastructure, background jobs, queues, or scheduled tasks.

Every candidate must have experience with at least one of the following: code review, pull requests, or issue tracking.

Every candidate must be able to write technical English.
```

#### Δ — annotate on diagram

- **Title line dropped**; “You” → **“Every candidate”** (third-person policy)
- Line 3 **split** into action types × API types (visible structural change)
- Line 6: comma-list → explicit **“at least one of the following”** list (6 items named)
- Line 8 shortened to **boolean-friendly** “write technical English”
- Plus: `wfm_handoffs/*.json` — proof the text was **chunk-reviewed**, not silently copied

---

## Stage 2 — Extraction (Phase 1)

**What happens:** Each normalized line becomes one **rule object** in JSON with template class, triggers, and logic trees.

**Edge label:** `English lines → Structured rule IR`  
**Magnitude:** ★★★★★ (biggest **semantic** invention: variables + logic)

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Format | Plain text | JSON | **new language** |
| Rules | 8 lines | 8 `rule_id`s (`R0001`…`R0008`) | 1:1 line mapping |
| Variables | **0** named in source | **~30–40** booleans/ints | invented vocabulary |
| Logic nodes per line | 0 | 1 trigger + 1…N condition nodes | trees |
| Shared gate | (implicit “candidate”) | explicit `is_candidate = true` on **every** rule | uniform template |
| File size | ~1.5 KB text | ~8–12 KB JSON | **~5–8×** |

#### BEFORE — one WFM line (line 2 only)

```text
Every candidate must have professional experience with at least one of the following: Python, Java, Go, C#, JavaScript, or TypeScript.
```

#### AFTER — `rules_extracted.json` rule `R0002` (real shape; trimmed)

```json
{
  "rule_id": "R0002",
  "template_class": "LOGICAL_IMPLICATION",
  "trigger_condition": { "kind": "atom", "variable": "is_candidate", "operator": "EQ", "value": true },
  "required_condition": {
    "kind": "or",
    "children": [
      { "kind": "atom", "variable": "has_prof_exp_python", "operator": "EQ", "value": true },
      { "kind": "atom", "variable": "has_prof_exp_java", "operator": "EQ", "value": true },
      { "kind": "atom", "variable": "has_prof_exp_go", "operator": "EQ", "value": true },
      { "kind": "atom", "variable": "has_prof_exp_c_sharp", "operator": "EQ", "value": true },
      { "kind": "atom", "variable": "has_prof_exp_javascript", "operator": "EQ", "value": true },
      { "kind": "atom", "variable": "has_prof_exp_typescript", "operator": "EQ", "value": true }
    ]
  }
}
```

#### BEFORE — line 1 only

```text
Every candidate must have at least 2 years of professional backend engineering experience.
```

#### AFTER — `R0001` (threshold + implication)

```json
{
  "rule_id": "R0001",
  "template_class": "LOGICAL_IMPLICATION",
  "trigger_condition": { "kind": "atom", "variable": "is_candidate", "operator": "EQ", "value": true },
  "required_condition": { "kind": "atom", "variable": "years_backend_experience", "operator": "GTE", "value": 2 }
}
```

#### Δ — annotate on diagram

- One English sentence → **one rule id** + **typed comparison** (`GTE 2`)
- “At least one language” → **OR of six boolean atoms** (not six English words)
- **`is_candidate` added** everywhere — not present in source text
- Line 6 in full file → **OR of six** experience booleans (`experience_automated_tests`, …)

---

## Stage 3 — Registry pass

**What happens:** Batched pass **merges aliases** and canonicalizes variable ids across all rules.

**Edge label:** `Ad-hoc names → Canonical registry`  
**Magnitude:** ★★★☆☆ (same JSON schema; **vocabulary** consolidates)

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Name authority | Per-rule extractor spelling | `identifier_registry.json` | single source of truth |
| Duplicate concepts | e.g. `experience_*` vs `has_*` | one `id` + `aliases[]` | fewer collisions at compile |
| IR file | `rules_extracted.json` | same path, **rewritten** in place | diff, not new extension |

#### BEFORE — extract-time names on `R0005` / `R0006` (fragment)

```json
"variable": "has_git_team_experience"
"variable": "experience_automated_tests"
"variable": "experience_debugging_production"
```

#### AFTER — registry + aligned IR (conceptual)

```json
// identifier_registry.json
{ "id": "has_git_team_experience", "aliases": ["Git in team development", "experience using Git in team development"], "line_hints": [5] }
{ "id": "years_backend_experience", "aliases": ["2+ years professional backend", "professional backend engineering experience"], "line_hints": [1] }

// rules still LOGICAL_IMPLICATION but names now consistent across R0001–R0008
```

#### Δ — annotate on diagram

- Human-readable phrases from NL → **stable snake_case ids**
- Cross-rule references **aligned** before Z3 sees the model
- New artifact: **`identifier_registry.json`** (~40–80 lines for Mini-BE8)

---

## Stage 3b — vNext lowering (compile-time)

**Edge label:** `Expansion templates → Core IR (solver)`  
**Magnitude:** ★★☆☆☆ (internal; assessment files **keep** pre-lowering copy)

| | BEFORE | AFTER |
|--|--------|-------|
| IR seen by humans | `K_OF_N`, `SUM_THRESHOLD`, … | unchanged in `rules_extracted.json` on disk |
| IR seen by Z3 | expansion nodes | flattened `or` / `and` / atoms |

**Diagram tip:** Draw as a **side branch** off compile, not a replacement file authors edit.

---

## Stage 4 — Compile + meta-scheme

**What happens:** Rules + pathway compiled into solver-ready **meta-scheme**.

**Edge label:** `Rule list → Pathway + compiled model`  
**Magnitude:** ★★★★☆

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Policy structure | 8 separate rules | 1 pathway **`must_satisfy_all`: [R0001…R0008]** | global AND |
| Semantics version | (implicit) | `"policy_semantics_version": "1.1"` | version stamp |
| Baseline | (implicit) | `DEFAULT_UNSATISFIED` | default outcome encoded |
| File | `rules_extracted.json` | `meta_scheme.json` | **new top-level contract** |

#### BEFORE — extract file header only

```json
{ "policy_id": "latest", "rules": [ { "rule_id": "R0001", "..." }, "..." ] }
```

#### AFTER — `meta_scheme.json` (excerpt)

```json
{
  "policy_id": "latest",
  "policy_semantics_version": "1.1",
  "baseline_evaluation": "DEFAULT_UNSATISFIED",
  "evaluation_pathways": [{
    "pathway_id": "compiled_default",
    "must_satisfy_all": ["R0001","R0002","R0003","R0004","R0005","R0006","R0007","R0008"],
    "must_not_trigger": []
  }],
  "rules": [ "... compiled bodies per rule_id ..." ]
}
```

#### Δ — annotate on diagram

- Scattered rules → **single hiring pathway** (all eight must hold)
- Adds **pathway_id** used later by external **sufficiency** gate

**On compile failure:** structural **Repairer_Piv** loops (IR patch, not NL).

---

## Stage 5 — Z3 check + English back-translation

**Edge label:** `Static model → SAT verdict + model summary`  
**Magnitude:** ★★★☆☆

#### BEFORE — `meta_scheme.json` (no runtime verdict yet)

```json
{ "evaluation_pathways": [{ "must_satisfy_all": ["R0001", "...", "R0008"] }], "rules": ["..."] }
```

#### AFTER — two new surfaces

**`z3_result.json`:**

```json
{ "status": "sat", "message": "Policy admits at least one model assignment under baseline pathway." }
```

**`synthetic_en.md` (excerpt — paraphrase of math, not copy-paste of phase0):**

```markdown
When is_candidate is true, the default pathway requires simultaneously:
- years_backend_experience ≥ 2;
- at least one of six language booleans;
- at least one API-type boolean among REST / GraphQL / internal service;
- … (all eight rule families) …
If any required condition on the pathway fails, baseline evaluation is unsatisfied.
```

#### Δ — annotate on diagram

- Adds **solver evidence** the policy is internally consistent (not vacuously broken)
- **`synthetic_en.md`** = second English layer derived from **math**, used by critic (≠ phase0 text)

---

## Stage 5b — Assessment linearization

**Edge label:** `JSON IR → Linearized audit lines`  
**Magnitude:** ★★★☆☆

#### BEFORE — `R0002` as JSON (opaque to reviewers)

```json
{ "rule_id": "R0002", "required_condition": { "kind": "or", "children": [ "...6 atoms..." ] } }
```

#### AFTER — one line in `linearized_model_for_assessment.txt`

```text
R0002 [LOGICAL_IMPLICATION] if is_candidate then (≥1 of: has_prof_exp_python, has_prof_exp_java, has_prof_exp_go, has_prof_exp_c_sharp, has_prof_exp_javascript, has_prof_exp_typescript)
```

#### Δ

- Same semantics, **new readable encoding** for tester/cross-critic
- Makes OR-width and rule ids **visible** without opening JSON

---

## Stage 6 — Precheck

**Edge label:** `Model + NL → Heuristic warnings`  
**Magnitude:** ★★☆☆☆ (overlay only)

#### BEFORE

```text
phase0_normalized_nl.txt  +  meta_scheme.json  (unchanged)
```

#### AFTER — `precheck.json`

```json
{
  "status": "ok",
  "warnings": [],
  "checks_run": ["constants_in_source", "rule_line_coverage"]
}
```

#### Δ — diagram as **stamp** on the pipeline, not a new policy representation

---

## Stage 7 — Tester (`--with-tester`)

**Edge label:** `NL vs linearized → Per-rule findings`  
**Magnitude:** ★★☆☆☆ (reports; optional IR patch via 7b)

#### BEFORE — two parallel views (unchanged files)

```text
Line 8 phase0: "Every candidate must be able to write technical English."
Linearized R0008: if is_candidate then can_write_technical_english = true
```

#### AFTER — `tester_report.json`

```json
{
  "verdict": "issues",
  "findings": [{
    "rule_id": "R0008",
    "severity": "medium",
    "summary": "NL emphasizes 'explain technical decisions clearly'; IR only exposes boolean can_write_technical_english."
  }]
}
```

#### Δ — **mismatch evidence** between human line and formal line (diagram: two columns → verdict bubble)

---

## Stage 7b — Test-repair (optional)

**Edge label:** `Findings → Patched rules_extracted.json`  
**Magnitude:** ★★★☆☆ when used

#### BEFORE — `R0008` atom only

#### AFTER — same rule with e.g. `assessment_mode: subjective_llm` or expanded atoms (operator-approved)

---

## Stage 8 — Semantic critic (`--with-critic`)

**Edge label:** `phase0 NL vs synthetic_en → PASS / DRIFT`  
**Magnitude:** ★★☆☆☆

#### BEFORE

```text
8-line phase0 policy  |  synthetic_en.md (whole-policy summary)
```

#### AFTER — `critic_result.txt`

```text
VERDICT: PASS
Notes: Pathway AND of eight rules; language OR-width matches six named languages.
```

#### Δ — **whole-policy** alignment check (broader than per-line tester)

---

## Stage 9 — Cross-critic + 9b repair + 10 post-cross

**Edge label:** `NL vs linearized structure → Structural findings`  
**Magnitude:** ★★☆☆☆ (+ ★★★ if cross-repair edits IR)

#### BEFORE — line 2 NL vs linearized

```text
NL:  "... at least one of the following: Python, Java, Go, ..."
LIN: "R0002 ... (≥1 of: has_prof_exp_python, ... has_prof_exp_typescript)"  // 6 atoms
```

#### AFTER — `cross_critic_report.json` finding

```json
{
  "finding_id": "XC-02",
  "rule_ids": ["R0002"],
  "issue": "Confirm six languages match NL list exactly (including TypeScript)."
}
```

**Post–cross:** semantic critic **re-runs** after IR edits — diagram as a **loop back** to stage 8.

---

## Stage 11 — IR structure / varprod guard

**Edge label:** `IR → Pass / block`  
**Magnitude:** ★★☆☆☆ — `ir_structure_check.json` overlay

---

## Stage 12 — Template suite

**Edge label:** `Policy model → Executable test scenarios`  
**Magnitude:** ★★★★☆

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Content | Abstract rules | **Concrete worlds** (bool/int assignments) | test data |
| Execution | none | Z3 per scenario | pass/fail counts |

#### BEFORE — policy-only (no instance)

```text
Rule R0001: years_backend_experience ≥ 2 when is_candidate
```

#### AFTER — `template_suite_generated.json` instance

```json
{
  "template_class": "scenario",
  "description": "Minimal satisfying candidate",
  "world": {
    "is_candidate": true,
    "years_backend_experience": 3,
    "has_prof_exp_python": true,
    "has_experience_postgresql": true,
    "has_git_team_experience": true
  },
  "golden": { "sat": true }
}
```

#### AFTER — `template_run_report.json`

```json
{ "passed": 12, "failed": 1, "errors": 0 }
```

#### Δ — policy becomes **machine-executable test cases** with golden SAT/UNSAT

---

## Stage 12b — Template repair (optional)

**Edge label:** `Failed tests → Patched IR` — loop back to compile/templates when operator approves.

---

## Stage 13 — External tester (CLI `--with-external-tester`)

**Edge label:** `CV prose → Numbered evidence → Partial world`  
**Magnitude:** ★★★★★

| Metric | BEFORE | AFTER | Δ |
|--------|--------|-------|---|
| Input | ~35 lines unstructured CV | numbered `external_tester_source.json` | segmentation |
| Variables | 0 in CV | 20+ policy variables with **provenance** | extraction |
| Unknowns | N/A | explicit `not_found` | honesty surface |

#### BEFORE — `backend_engineer_cv.txt` (excerpt)

```text
Backend Engineer
Northstar Analytics
March 2022 – Present
Built and maintained backend services in Python and TypeScript.
Developed REST APIs for customer accounts, billing events, and reporting workflows.
Worked with PostgreSQL for schema changes, query debugging, and data migrations.
Wrote automated tests for API endpoints, background jobs, and database logic.
Used Git, pull requests, code reviews, Jira tickets, and CI checks in daily work.
```

#### AFTER — `external_world.json` assignments (illustrative)

```json
{
  "years_backend_experience": { "value": 4, "provenance": "stated", "source_line": 3 },
  "has_prof_exp_python": { "value": true, "provenance": "stated", "source_line": 4 },
  "has_prof_exp_typescript": { "value": true, "provenance": "stated", "source_line": 4 },
  "has_experience_postgresql": { "value": true, "provenance": "stated", "source_line": 6 },
  "experience_cloud_infrastructure": { "value": null, "provenance": "not_found" },
  "experience_scheduled_tasks": { "value": null, "provenance": "not_found" }
}
```

#### Δ — resume **mapped onto policy vocabulary**; gaps explicit (not guessed)

---

## Stage 14 — Policy-case pipeline (v4 + tiers)

**Edge label:** `Partial world → Sufficiency → Tier verdicts`  
**Magnitude:** ★★★★★ (adds **gates** strong/weak CV divergence)

| Metric | Strong CV | Weak CV |
|--------|-----------|---------|
| `grounded_stated` | ~18–21 | ~6 |
| `grounded_missing` | few | ~22 |
| Tier 1 | may run SAT | often **blocked** |
| Final outcome | `compatible` | `incompatible` or `blocked_insufficient_evidence` |

#### BEFORE — same CV prose as stage 13

#### AFTER (weak CV) — `policy_case_sufficiency.json` + `policy_case_report.json`

```json
// sufficiency
{
  "must_satisfy_all": ["R0001","R0002","R0003","R0004","R0005","R0006","R0007","R0008"],
  "grounded_variables_required": 28,
  "grounded_stated": 6,
  "grounded_missing": ["has_prof_exp_go", "has_experience_mysql", "experience_cloud_infrastructure", "..."],
  "sufficient_for_strict_query": false
}

// report
{
  "outcome": "blocked_insufficient_evidence",
  "tier1": { "status": "blocked", "reason": "pathway_sufficiency" },
  "tier3": { "verdict": "incompatible" }
}
```

#### AFTER (strong CV) — contrast for diagram **fork**

```json
{
  "outcome": "compatible",
  "tier1": { "status": "sat", "pathway": "compiled_default" },
  "tier3": { "verdict": "compatible" }
}
```

#### Δ — annotate on diagram

- **Sufficiency gate** prevents “missing evidence” from looking like “policy impossible”
- **Three tiers:** grounded SAT → programmatic derive → speculative LLM audit
- Artifacts: `policy_case_world.json`, `policy_case_narrative.md`, tier addendum files

**Artifacts per case run:** `policy_case_world.json`, `policy_case_sufficiency.json`, `policy_case_tier_addendum.json`, `policy_case_programmatic_fill.json`, `policy_case_speculative_audit.json`, `policy_case_narrative.md`, `policy_case_report.json`

---

## End-to-end flow (ASCII — copy-friendly for diagram tools)

```
[Reference Markdown]
        |
        v  (optional)
 [Scope Rewriter] ---> latest.nl + latest.json
        |
        v
 [Pivot WFM Phase 0] ---> phase0_normalized_nl.txt
        |
        v
 [Extract Phase 1] ---> rules_extracted.json
        |
        v
 [Registry] ---> identifier_registry.json + aligned rules
        |
        v
 [Compile + vNext lower] ---> meta_scheme.json
        |     \-- (fail) --> [Structural Repairer_Piv] --+
        v                                                  |
 [Z3 SAT check] ---> z3_result.json                       |
        |                                                  |
        v                                                  |
 [Precheck] ---> precheck.json                             |
        |                                                  |
        +--> [--with-tester] ---> tester_report            |
        +--> [--with-critic] ---> critic / synthetic_en    |
        +--> [--with-cross-critic] ---> cross + repair     |
        +--> [template suite] ---> template_run_report     |
        |                                                  |
        v                                                  |
 [External / policy-case] ---> policy_case_*.json          |
   (CV / unstructured evidence)                            |
```

---

## Suggested prompts for ChatGPT visualization

1. **Transformation swimlane:** One lane per stage 0→14. On **every** arrow, paste the stage’s **Edge label** + **Magnitude ★** + **Δ bullets** from this doc. Put **BEFORE** on the left node and **AFTER** on the right node (use the metric tables where counts matter).

2. **Before/after strip (best for “how much changes”):** Horizontal strip with 8–10 columns: `MD spec` → `latest.nl` → `phase0` → `rules_extracted` → `meta_scheme` → `linearized` → `synthetic_en` → `CV prose` → `policy_case_world`. Under each column, show **one line** of Mini-BE8 (line 2 languages is ideal — watch OR explode). Annotate **variable count** under extract (0 → 6 atoms for one line).

3. **Strong vs weak fork:** After stage 14, split diagram: same policy, two CV inputs, two `policy_case_report.json` outcomes (`compatible` vs `blocked_insufficient_evidence`).

4. **Decision diamond:** Sufficiency `sufficient_for_strict_query` → tier1 blocked vs SAT; tier3 only labeled “speculative” when tier1 blocked.

---

## Where files live on disk (convention)

| Stage | Typical directory |
|--------|-------------------|
| Scope rewriter | `NagV/exports/scope_rewriter/<run>/scope_rewriter/` |
| Full pivot run | `NagV/exports/pivot_runs/<run>_wfm/` |
| Policy-case only | `.../policy_cases/<case_name>/` (reuse parent run’s `rules_extracted.json`) |

Example real run (same policy family as Mini-BE8): `NagV/exports/pivot_runs/Backend_Engineer2_v1_wfm/`.

---

## Glossary (short)

| Term | Meaning |
|------|---------|
| **NL** | Natural language rule lines |
| **IR** | JSON rule objects (`rules_extracted.json`) |
| **Meta-scheme** | Compiled policy + pathways + rule bodies for solver |
| **Pathway** | Which rules must all hold together (`must_satisfy_all`) |
| **WFM** | Way-Forward Module — Phase 0 chunk normalization |
| **DRIFT** | Semantic critic verdict: English vs model summary disagree |
| **CWA** | Closed-world assumption: unknown grounded → false/0 |
| **Grounded** | Variable directly evidenced from source text (tier 1) |
| **Derived** | Inferred from other stated facts via policy rules (tier 2) |

---

*Document version: 2026-05-23 (rev 2) — transformation blocks with BEFORE/AFTER, metrics, and Δ bullets for diagram construction.*
