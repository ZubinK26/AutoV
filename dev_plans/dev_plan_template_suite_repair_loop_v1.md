# Dev plan: Template-suite repair loop — diagnose, triage, align IR, re-verify (v1)

**Status:** Ready for implementation  
**Priority:** P1  
**Problem:** Pivot Tester, semantic critic, and CrossCritic can all **PASS** while **executable template tests** expose NL ↔ compiled-semantics gaps (vacuous K_OF_N lowering, shared `result_variable`, inconsistent triggers, wrong goldens). Operators need a **fourth repair loop** with the same interactive spirit as Tester / Critic / Cross repair.  
**Motivation (Backend Engineer2):** `gen_008` pairwise — processed NL requires ≥1 language; lowered R0002 is vacuously satisfied when all language flags are false. Other critics did not flag this; template suite did.

**Related:** `dev_plan_test_repairer_interactive_v1.md`, `dev_plan_pivot_cross_critic_cross_repairer.md`, `dev_plan_k_of_n_way_b_in_place_enforcement_v1.md`, `PIVOT_TEMPLATE_SYSTEM.md`, `template_suite/diff.py`, `template_run_report.json`.

---

## 1. Vision (one paragraph)

After the template generator runs and `template_run_report.json` contains **fail** or **inconclusive** instances, a **Template Diagnostician** turns raw diffs into **human-readable findings** (NL pointer, rule ids, why golden vs actual diverged, policy vs test blame). The operator **triages** each finding (approve / ignore / quit). On **REPAIR**, a **Template Repairer** patches **`rules_extracted.json`** (primary) using processed NL + linearized model + approved findings only — with the same IR validation and compile/registry gates as other repairers. Then the pipeline **re-verifies in order**: Pivot Tester → semantic critic → CrossCritic → **re-run template suite**. Loop until tests are clean, operator types **PROCEED_INCOMPLETE**, or max rounds. Operator may **skip** findings (e.g. wrong golden, acceptable inconclusive) so repair feedback stays precise.

---

## 2. Problem statement

| Gap today | Example |
|-----------|---------|
| Template run is **non-fatal** (`template_suite_ok` may be true with failed > 0) | BE2: 5 pass, 2 fail, 1 inconclusive — pipeline continues |
| No **LLM explanation** of template diffs in terminal | Operator reads JSON `diff.detail` manually |
| No **repair agent** for semantics exposed by tests | gen_008 needs IR fix (mandatory k-of-n / global aggregate), not critic drift |
| No **triage** of which test failures count as policy bugs | gen_003 attribution golden is wrong — should be **ignored**, not drive IR edits |
| No **closed loop** re-checking tester/critic/cross after template-driven IR change | Risk of fixing Z3 locally but re-breaking NL alignment |

**Goal:** Close the loop so “simple policy, small misalignment” is caught and fixed **before** external tester, without weakening other repair agents’ scopes.

---

## 3. Names and artifacts

| Component | Name |
|-----------|------|
| Audit + explain (LLM) | **Template Diagnostician** |
| Repair LLM agent | **Template Repairer** |
| Interactive loop module | `template_interactive_loop.py` |
| Diagnostician module | `template_diagnostician_agent.py` |
| Repairer module | `template_repairer_agent.py` |
| Prompts | `prompts/template_diagnostician.md`, `prompts/template_repairer.md`, `prompts/template_repairer_ir_addendum.md` |
| Structured report | `template_diagnostic_report.json` |
| Raw LLM | `template_diagnostic_result.txt` |
| Handoff (approved findings only) | `template_repair_handoff.json` |
| Trace | `template_repairer_trace.jsonl` |
| Rules snapshot | `rules_after_template_repair.json` |

**Tokens (reuse):** `REPAIR`, `PROCEED_INCOMPLETE`, abort via empty line / `q` — same as tester/critic/cross gates (`REPAIR_CRITIC_DRIFT_TOKEN`).

---

## 4. Pipeline placement

```text
… → Z3/precheck → tester [+ test-repair loop]
  → semantic critic [+ semantic repair loop]
  → cross critic [+ cross-repair loop]
  → template generator → run_template_suite → template_run_report.json
  → [template diagnostic + repair loop]   ← NEW
  → external tester (optional)
```

**Invariant:** Template repair runs **after** cross-coherence segment (when enabled) and **after** first template suite run. It **does not** replace tester/critic/cross; it **re-runs** them after IR changes.

**Default:** Off (`--with-template-repair` + interactive flag). Template suite alone stays non-blocking unless product later adds `--fail-on-template-findings`.

---

## 5. Inputs the agents must see

### 5.1 Deterministic (always)

| Artifact | Use |
|----------|-----|
| `template_run_report.json` | fail/inconclusive `results[]` with `instance_id`, `template_kind`, `actual`, `golden`, `diff` |
| `template_suite_generated.json` (or `--template-suite` path) | Full instance: `world`, `query`, `golden`, `world_base` / `world_mutant`, etc. |
| `phase0_normalized_nl.txt` (or `nl_after_extract_rewrites.txt` if present) | **Processed NL** — authoritative wording |
| `rules_extracted.json` | Current IR |
| `linearized_model_for_assessment.txt` or `build_and_write_linearized` output | Per-rule compiled view |
| `meta_scheme.json` / pathway | Active rule ids |

### 5.2 Per failing instance (deterministic pre-bundle)

Build **`template_failure_bundle.json`** (or inline in diagnostician payload) per `instance_id`:

- `template_kind`, `world` pins, `query`, `golden`, `actual`, `diff.detail`
- `linearized_excerpt` for `query.rule_id` when applicable
- `nl_line_candidates` — heuristic map instance vars → NL lines (optional v1: LLM only)

### 5.3 LLM Diagnostician output

Structured findings (Pydantic), analogous to `CrossCriticReport`:

```json
{
  "schema_version": "1",
  "verdict": "ISSUES",
  "suite_summary": { "passed": 5, "failed": 2, "inconclusive": 1 },
  "findings": [
    {
      "id": "TS001",
      "severity": "critical",
      "category": "policy_vs_nl",
      "instance_ids": ["gen_008"],
      "rule_ids": ["R0002"],
      "nl_pointer": "line 3: at least one backend programming language",
      "explanation": "…",
      "recommendation": "…",
      "blame": "policy_ir",
      "repair_target": "rules"
    }
  ]
}
```

**`blame` enum (v1):**

| Value | Meaning | Typical repair |
|-------|---------|----------------|
| `policy_ir` | Compiled rules ≠ NL intent | Patch `rules_extracted.json` |
| `template_golden` | Engine consistent; golden/world wrong | Optional suite patch (v1.1) or **ignore** |
| `template_world` | Instance pins inconsistent | Fix suite instance (v1.1) or ignore |
| `inconclusive_ambiguous` | Executor could not label (e.g. base UNSAT) | Policy and/or golden; operator decides |

**Default repair agent scope (v1):** only findings with `blame=policy_ir` and `repair_target=rules` are eligible for Template Repairer. Others are explain-only unless operator overrides (v1.1).

---

## 6. Template Diagnostician

### 6.1 Role

- Consume **only** fail/inconclusive instances (passing tests are listed in summary, not expanded).
- Explain **why** `diff` occurred in plain language (terminal + JSON).
- Classify **blame** so triage is informed (policy vs golden vs inconclusive).
- Propose **recommendation** text reused in repair handoff (not a second LLM story).

### 6.2 Prompt focus (`template_diagnostician.md`)

- Compare **processed NL** obligation to **linearized rule** + **template_kind** semantics (see `PIVOT_TEMPLATE_SYSTEM.md`).
- Known patterns (checklist):
  - **Vacuous K_OF_N lowering:** `Implies(OR(clauses), result)` — all clauses false ⇒ rule satisfied; NL “must have ≥1” not enforced.
  - **Missing global aggregate:** mandatory “every candidate” line needs `K_OF_N` + `result_variable` **and** pathway-level requirement on aggregate (Way B).
  - **Shared `result_variable`** across distinct K_OF_N rules (X001-style).
  - **Stray triggers** (`is_candidate`, `applicant_position`) on subset of lines only.
  - **Rule attribution template:** golden expects single rule; engine lists all satisfied rules in witness.
  - **Counterfactual:** mutant/base worlds flip wrong variable for queried rule.
- **Do not** duplicate full tester/critic/cross jurisdiction — cite “cross-rule outcome split” only if visible in linearized + test diff.

### 6.3 Terminal UX

`format_template_diagnostic_terminal(report, *, report_path=..., suite_path=...)`:

```text
Template suite: 5 passed, 2 failed, 1 inconclusive (see template_run_report.json)

Finding 1 of 3: [TS001] critical / policy_vs_nl
  Instances: gen_008 (pairwise)
  Rules: R0002
  NL: line 3 — at least one backend programming language …
  Problem: …
  Recommendation: …
  Blame: policy_ir → repair rules_extracted.json
```

---

## 7. Interactive workflow (mirror tester/cross)

### 7.1 When all template tests pass

No gate. Write `template_diagnostic_report.json` with `verdict: PASS` (optional skip LLM). Continue pipeline.

### 7.2 When fail + inconclusive > 0

**Requires:** `--interactive-template-suite` **or** `--interactive-policy` (v1: same pattern as `--interactive-tester`).

1. Run **`run_template_diagnostician`** → save JSON + print terminal findings.
2. **Per-finding triage** (mandatory before REPAIR):

```text
Finding 1 of 3: [TS001] critical / policy_vs_nl — gen_008 …
  a = approve for repair   i = ignore   q = quit triage
```

- **Approve:** finding id added to `approved_finding_ids`.
- **Ignore:** excluded from handoff (e.g. gen_003 golden too strict).
- **Quit triage:** return to main gate without changing approvals.

3. **Main gate:**

```text
Approved: TS002, TS003 | Ignored: TS001

Type REPAIR to run Template Repairer on approved policy_ir findings, then re-verify (tester → critic → cross → template suite).
Type PROCEED_INCOMPLETE to continue without template repair (writes handoff for audit).
Press Enter to abort.
```

4. **`REPAIR`:** build `template_repair_handoff.json` → Template Repairer → apply (§8) → verification chain (§9) → loop to step 1 (re-diagnose or re-run suite only — **v1: re-run suite + optional re-run diagnostician if still failing**).

5. **`PROCEED_INCOMPLETE`:** set `summary["user_consented_template_issues"] = true`; continue (e.g. external tester).

6. **Abort:** `blocked_template_repair` or `blocked_template_diagnostic`.

**Non-interactive:** unchanged — print summary counts only; no repair (document explicitly).

### 7.3 Handoff schema (`template_repair_handoff.json` v1)

```json
{
  "handoff_schema_version": "1",
  "approved_finding_ids": ["TS002"],
  "ignored_finding_ids": ["TS001"],
  "findings": [ … approved only … ],
  "processed_nl_path": "…",
  "template_run_report_path": "…",
  "suite_path": "…",
  "rules_sha256_before": "…"
}
```

---

## 8. Template Repairer

### 8.1 Scope (strict)

| In scope | Out of scope |
|----------|----------------|
| Patch **`rules_extracted.json`** for approved `policy_ir` findings | Rewriting processed NL |
| `K_OF_N` + `result_variable`, trigger alignment, unique aggregates, encodable templates | Full template suite regeneration |
| Focus rules from finding `rule_ids` | Tester/critic/cross finding types |
| Same sanitize + `repair_ir_validation.py` as Test/Cross repair | `PIVOT_REPAIR_ALLOW_APPEND_RULES` unless env on |

### 8.2 Prompt stack

- `template_repairer.md` — mode `template_suite_alignment`
- `repairer_ir_normative.md` + `template_repairer_ir_addendum.md` (K_OF_N Way B, no illegal top-level keys, no vacuous-only fixes that leave NL unenforced)
- `extractor_vnext_addendum.md` / temporal appendices when `pivot_ir_extensions` present
- **Input JSON:** `policy_id`, `handoff.findings`, `processed_nl_excerpt`, `linearized_excerpt`, `rules` (focus bodies + stubs), per-finding `instance_id` + `diff` + `recommendation`

### 8.3 Apply path (same mechanical core)

1. Parse `RepairerPivOutput`-shape `{ "rules", "change_summary" }`.
2. **`validate_repair_round`** / focus-rule merge via existing `test_repairer` / `cross_repairer` merge helper (extract shared `apply_repairer_rules` if not already).
3. Optional **registry** (skip when slug set unchanged).
4. **`load_rules_and_compile`** → `rules_extracted.json`, `meta_scheme.json`, `z3_result.json`, `synthetic_en.md`.
5. **precheck**, varprod refresh, **rebuild linearized** artifacts.
6. Write **`rules_after_template_repair.json`**, append **`template_repairer_trace.jsonl`**.

**Retries:** `PIVOT_TEMPLATE_REPAIR_COMPILE_ATTEMPTS` (default **5**), `PIVOT_TEMPLATE_REPAIR_REGISTRY_ATTEMPTS` (default **3**).

**Stall detection:** same pattern as semantic repair if identical compile error repeats (`PIVOT_TEMPLATE_REPAIR_STALL_THRESHOLD`).

### 8.4 Finding → IR mapping hints (addendum)

| Category | Allowed edits |
|----------|----------------|
| `policy_vs_nl` + vacuous k-of-n | Add/fix `result_variable`; optional companion `CONSTANT_RELATIONAL` on aggregate for global lines; do **not** only nest OR under implication without aggregate enforcement |
| `variable_collision` | Distinct `result_variable` per K_OF_N rule |
| `trigger_inconsistency` | Remove stray `is_candidate` / align all “every candidate” as global |
| `template_golden` | **No-op in v1** — finding should have been ignored |

---

## 9. Post-repair verification chain (required)

After successful compile, **in order** (skip step if flag off in run, but template loop **requests** all when enabled in original run):

| Step | Action | Artifact refresh |
|------|--------|------------------|
| 1 | **Pivot Tester** | `tester_report.json`, linearized |
| 2 | **Semantic critic** | `critic_report.json` — interactive DRIFT gate **not** re-opened automatically unless critic fails (v1: run once; if DRIFT, print warning and return to operator — do not nest semantic repair inside template loop without product sign-off) |
| 3 | **CrossCritic** | `cross_critic_report.json` — same: report only, no auto cross-repair in v1 |
| 4 | **Template suite** | Re-run `run_template_suite` on **same** `template_suite_generated.json` path → new `template_run_report.json` |

**v1 policy:** Template repair loop **re-runs audits**; if tester/critic/cross regress, print clear message and return to main template gate (operator may PROCEED or abort). **Do not** auto-invoke Test-Repairer / CrossRepairer inside template loop (avoid repair combinatorics).

**Success condition for loop exit:** `template_run_report.summary.failed == 0` and `inconclusive == 0` (or operator `PROCEED_INCOMPLETE`).

**Optional env:** `PIVOT_TEMPLATE_REPAIR_REVERIFY_CRITIC=0` to skip critic/cross re-run (dev only).

---

## 10. Orchestration (`run.py` + CLI)

### 10.1 New kwargs / flags

| Flag | Default | Meaning |
|------|---------|---------|
| `--with-template-repair` | off | Enable template diagnostic + repair loop after suite run |
| `--interactive-template-suite` | off | Triage + REPAIR gate (or use `--interactive-policy`) |
| `--fail-on-template-findings` | off | CI: exit `blocked_template` if fail/inconclusive > 0 and no repair |

**Constraints:**

- `--with-template-repair` requires template suite to have run (`template_run_report.json` exists or run suite first in same invocation).
- `--with-template-repair` without interactive: diagnostician may still run (optional env `PIVOT_TEMPLATE_DIAGNOSTIC_ON_FAIL=1` default on) for JSON only; no repair.

### 10.2 `run.py` block (after existing template suite block)

```python
if with_template_repair and summary.get("template_run_report"):
    rules, meta, ... = run_template_interactive_loop(
        work_dir=work_dir,
        nl_text=nl_text_for_artifacts,
        interactive=interactive_policy or interactive_template_suite,
        with_template_repair=True,
        reverify_tester=with_tester,
        reverify_critic=not skip_critic,
        reverify_cross=with_cross_critic,
        ...
    )
```

### 10.3 Standalone entry (replay)

`pivot-template-repair` → `template_repair_cli.py`:

```text
python -m pivot_pipeline.template_repair_cli \
  --work-dir NagV/exports/pivot_runs/Backend_Engineer2_v1_wfm \
  --input NagV/exports/scope_rewriter/Backend_Engineer2_run/scope_rewriter/latest.nl \
  --rules-json …/rules_extracted.json \
  --suite …/template_suite_generated.json \
  --interactive-template-suite
```

Requires existing `template_run_report.json` or `--rerun-suite` to execute tests first.

---

## 11. Example operator session (BE2)

1. Pipeline runs template suite → gen_008 fail, gen_003 fail, gen_005 inconclusive.
2. Diagnostician prints:
   - **TS001** `template_golden` — gen_003 attribution (ignore).
   - **TS002** `policy_vs_nl` — gen_008 vacuous R0002 (approve).
   - **TS003** `inconclusive_ambiguous` — gen_005 wrong counterfactual variable (ignore or approve if policy fix is unify R0001 global).
3. Operator approves **TS002** only → REPAIR.
4. Template Repairer adds distinct result vars / global aggregate enforcement on R0002 per Way B.
5. Re-verify: tester PASS, critic PASS, cross PASS, template suite 8/8 pass.
6. Continue to external tester.

---

## 12. Tests (v1)

| Test | Intent |
|------|--------|
| `test_template_diagnostic_from_fixture_report` | Mock LLM → structured findings; blame classification |
| `test_template_handoff_filters_approved` | ignored ids excluded |
| `test_template_repair_vacuous_k_of_n_fixture` | Mock repair: R0002 gets enforceable aggregate; pairwise B → unsatisfied |
| `test_template_loop_rerun_suite_pass` | Second suite run passes after mock repair |
| `test_cli_with_template_repair_requires_suite` | CLI validation |
| `test_format_template_diagnostic_terminal` | Snapshot key lines |

Use fixtures under `tests/fixtures/template_repair/` (minimal rules + 2-instance suite mirroring gen_008).

---

## 13. Non-goals (v1)

- Auto-editing `template_suite_generated.json` without explicit v1.1 `repair_target=suite` + operator approve per finding.
- Replacing template generator.
- Z3 invariant template generation.
- Nesting Test-Repairer / CrossRepairer / Semantic repair inside template loop.
- External tester re-run inside template loop (operator re-runs separately).

---

## 14. Docs / diagram updates

| File | Change |
|------|--------|
| `pivot_pipeline/README.md` | Flags, env vars, example commands |
| `ARCHITECTURE.md` | Template repair loop box in post-model diagram |
| `diagrams/pipeline_e2e_overview.md` | Step after template suite |
| `PIVOT_TEMPLATE_SYSTEM.md` | Cross-link vacuous trigger + attribution semantics for diagnostician |

---

## 15. Env vars (summary)

| Env | Default | Meaning |
|-----|---------|---------|
| `PIVOT_TEMPLATE_REPAIR_MAX_ROUNDS` | 3 | Interactive repair loops |
| `PIVOT_TEMPLATE_REPAIR_COMPILE_ATTEMPTS` | 5 | Per REPAIR |
| `PIVOT_TEMPLATE_REPAIR_REGISTRY_ATTEMPTS` | 3 | Registry retries |
| `PIVOT_TEMPLATE_DIAGNOSTIC_ON_FAIL` | 1 | Run diagnostician LLM when fail/inc > 0 |
| `PIVOT_TEMPLATE_REPAIR_REVERIFY_CRITIC` | 1 | Re-run critic+cross after repair |

---

## 16. Phased delivery

| Phase | Deliverable |
|-------|-------------|
| **P0** | Diagnostician agent + report schema + terminal formatter + deterministic failure bundles |
| **P1** | Interactive triage + handoff + Template Repairer + apply path + `rules_after_template_repair.json` |
| **P2** | Post-repair verification chain wired in `run.py` |
| **P3** | CLI `pivot-template-repair`, tests, docs |
| **P4 (optional)** | Suite/golden repair path for `blame=template_golden` with separate prompt mode |

---

## 17. Success criteria

- Operator can **ignore** gen_003-style golden mismatches and **repair** gen_008-style IR gaps in one session.
- After REPAIR, **tester + critic + cross + template suite** are re-run automatically; regressions are visible.
- No approved finding may patch rules without **processed NL excerpt** and **repair_ir_validation** pass.
- Backend Engineer2 (or successor work-dir) reaches **0 failed / 0 inconclusive** on template suite after approved policy_ir repairs, without manual JSON surgery.
