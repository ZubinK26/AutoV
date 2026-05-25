# Dev plan: Test-Repairer + interactive tester repair loop (v1)

## Status

| Area | Status |
|------|--------|
| **Problem / role definition** | This document |
| **`tester_repairer_agent.py` + `prompts/test_repairer.md`** | Done |
| **`tester_interactive_loop.py` (tester → triage → repair → re-test)** | Done |
| **Per-finding approve / ignore UI** | Done |
| **`run.py` orchestration + CLI flags** | Done |
| **`pivot-tester` / replay entry wiring** | Done |
| **Tests + docs** | Done |

---

## Problem

**Pivot Tester** (`--with-tester`) now audits **processed NL ↔ linearized IR** and writes `tester_report.json`. On `verdict: "issues"` the pipeline either:

- exits with **`blocked_tester`** when `--fail-on-tester-findings`, or
- continues with no repair path (unlike **pivot critic → Repairer_Piv** or **CrossCritic → CrossRepairer**).

Operators need the same **interactive repair workflow**: see findings, choose repair vs proceed vs abort, and run an LLM **repair agent** that patches `rules_extracted.json` with the same apply/recompile/artifact refresh pattern.

**Additional requirement (v1):** **Per-finding triage** — for reports with multiple findings (e.g. T001–T003), the user can **approve** some for repair and **ignore** others. **Test-Repairer** receives **only approved findings**, not the full tester report.

**Example motivation:** Recruitment policy flagged **T001** (`misalignment` from unless → R0005 + R0008 PREEMPTION split) while logic is correct; operator may **ignore T001** and proceed, or approve only a **critical** threshold finding if present alongside benign structural noise.

---

## Names

| Component | Name |
|-----------|------|
| Audit stage | **Pivot Tester** (existing) |
| Repair LLM agent | **Test-Repairer** |
| Module | `test_repairer_agent.py` |
| Prompt | `prompts/test_repairer.md` |
| Interactive loop module | `tester_interactive_loop.py` |
| Handoff on disk | `tester_repair_handoff.json` (approved findings only) |
| Trace | `test_repairer_trace.jsonl` |
| Patched rules snapshot | `rules_after_test_repair.json` |

Reuse token **`REPAIR`** (`REPAIR_CRITIC_DRIFT_TOKEN`) and **`PROCEED_INCOMPLETE`** for parity with critic/cross gates unless a dedicated **`PROCEED_TESTER_ISSUES`** is added — **v1: reuse existing tokens** to avoid operator confusion.

---

## Pipeline placement (ordering invariant)

```text
… → precheck → [linearize] → tester → [test-repair loop] → pivot critic → …
```

- Tester **still runs before pivot critic** (unchanged).
- Test-Repairer runs **only after** tester reports `issues` and operator chooses repair (or non-interactive policy allows auto-repair — **v1: interactive only**, mirror cross-repair default).
- After successful repair: **recompile → Z3 → synthetic → precheck → varprod → rebuild linearization → re-run tester** (same spirit as post–cross-repair semantic critic refresh).

---

## Relationship to other repair agents

| Agent | Handoff from | Fixes |
|--------|----------------|-------|
| **Repairer_Piv (semantic)** | Pivot critic DRIFT | NL ↔ synthetic / structural drift |
| **CrossRepairer** | CrossCritic ISSUES | Cross-rule IR coherence |
| **Test-Repairer** | Tester `issues` (**approved findings only**) | NL ↔ linearized **per-rule content** mismatches |

Test-Repairer **must not** broaden scope into cross-rule outcome splits (cross-repairer) or pathway/preemption skeleton without content mismatch (pivot critic).

---

## Interactive workflow (v1)

### A. When tester returns `ok`

No gate. Continue to pivot critic (if enabled). Write `tester_report.json` only.

### B. When tester returns `issues`

**Non-interactive** (no `--interactive-policy` and no new `--interactive-tester`):

- Behavior unchanged: optional `--fail-on-tester-findings` → `blocked_tester`; else record `tester_verdict: issues` and continue (document explicitly — today continue is allowed without `--fail-on-tester-findings`).

**Interactive** (`--interactive-policy` **or** `--interactive-tester`):

1. Print **`format_tester_report_terminal(report)`** (existing).
2. Enter **finding triage** sub-loop (new).

#### Finding triage UI

For each finding in `tester_report.json` (ordered by `id`):

- Show: `[T001] severity / category`, `nl_pointer`, `formal_pointer`, one-line `explanation`.
- Prompt per finding (or batch menu — implement **per-finding** as primary):

```text
Finding 1 of 3: [T001] warn / misalignment — …
  a = approve for repair   i = ignore   q = quit triage (back to main gate)
```

Default before triage: all findings **pending** (not approved, not ignored).

After triage, show summary:

```text
Approved for repair: T001
Ignored: T002, T003
```

3. **Main gate** (after triage):

```text
[policy gate] Tester reported issues (N total; M approved for repair).
  Type 'REPAIR' to run Test-Repairer on approved findings only, then re-run Tester.
  Type 'PROCEED_INCOMPLETE' to continue without repair (writes tester_repair_handoff.json with approvals/ignores for audit).
  Press Enter to abort.
```

4. **`REPAIR` with M = 0:** print hint; do not call LLM; return to triage or main gate.

5. **`REPAIR` with M ≥ 1:** build handoff → Test-Repairer → apply rules (below) → refresh artifacts → **re-run tester** → loop to step 1 until `ok`, `PROCEED_INCOMPLETE`, abort, or max rounds.

6. **`PROCEED_INCOMPLETE`:** set `summary["user_consented_tester_issues"] = True`, write handoff JSON (full report + `approved_finding_ids` + `ignored_finding_ids`), continue pipeline without repair.

7. **Enter / empty:** `PivotPipelineUserAbort` (same as critic).

#### Bounded repair rounds

- Env **`PIVOT_TESTER_REPAIR_MAX_ROUNDS`** (default **3**, clamp 1–10), same pattern as `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX` / `PIVOT_CROSS_REPAIR_MAX_ROUNDS`.
- Env **`PIVOT_TESTER_REPAIR_COMPILE_ATTEMPTS`** per REPAIR invocation (default **3**), reuse `complete_repairer_prompt` retry pattern from `repairer_piv_agent.py`.

---

## Handoff schema (`tester_repair_handoff.json` v1)

Written before Test-Repairer call and on `PROCEED_INCOMPLETE`.

```json
{
  "handoff_schema_version": "1",
  "source": "pivot_tester",
  "source_note": "user approved repair subset",
  "verdict": "issues",
  "compared_against": "processed_nl_and_linearized_model",
  "approved_finding_ids": ["T001"],
  "ignored_finding_ids": ["T002", "T003"],
  "findings": [ "... only approved finding objects ..." ],
  "full_report_path": "<work_dir>/tester_report.json",
  "notes": ""
}
```

Test-Repairer input JSON uses **`handoff.findings`** only (approved). Include **`ignored_finding_ids`** in payload so the model knows **not** to “fix” ignored items.

Extend **`tester_handoff_from_report()`** in `post_model_workflow.py` or add **`tester_repair_handoff_dict(report, *, approved_ids, ignored_ids)`** in `test_repairer_agent.py`.

---

## Test-Repairer agent

### Prompt (`prompts/test_repairer.md`)

Mirror **CrossRepairer** structure:

- **Input JSON:** `mode: "tester_nl_alignment"`, `policy_id`, `handoff` (approved findings only), `processed_nl_excerpt`, `linearized_excerpt`, `rules`.
- **Normative IR shape:** same bullets as `cross_repairer.md` / `repairer_piv_semantic.md` (single `target_rule_id` per PREEMPTION, etc.).
- **Discipline:**
  - Fix **only** approved `finding_id`s; one finding → minimal edit when possible.
  - Ground changes in **processed NL** and **linearized** lines cited in `formal_pointer` / `nl_pointer`.
  - **Do not** “fix” 1:1 line-count `misalignment` by deleting valid PREEMPTION splits unless the finding explicitly requires consolidation **and** NL supports a single-rule encoding within schema.
  - Prefer editing **existing rule bodies** over adding/deleting rules; if finding is `omission` / extra rule, allow add/remove with `change_summary` justification.
- **Output:** `{ "rules": [...], "change_summary": [ { "finding_id", "rule_id", "change" }, ... ] }` — reuse **`RepairerPivOutput`** Pydantic model.

### Module (`test_repairer_agent.py`)

```python
def run_test_repairer(
    *,
    policy_id: str,
    rules: list[dict],
    handoff: dict,
    processed_nl_excerpt: str,
    linearized_excerpt: str,
    llm=...,
) -> tuple[RepairerPivOutput, bool]

def append_test_repairer_trace(work_dir, record) -> None
def test_repair_max_rounds() -> int
```

Implementation: same **`complete_repairer_prompt`** helper as cross-repairer (JSON parse retry).

---

## Apply path (shared with cross / semantic repair)

Extract **`apply_repaired_rules(...)`** helper in `run.py` or `repair_apply.py` if duplication becomes painful; **v1** may inline copy from cross-repair block:

1. Validate `RepairerPivOutput` → assign `rules`.
2. Optional **`registry_pass_from_nl_and_rules`** when not `skip_registry`.
3. **`load_rules_and_compile`** → write `rules_extracted.json`, `meta_scheme.json`.
4. **`run_z3_check`** → `z3_result.json`.
5. **`meta_scheme_to_markdown`** → `synthetic_en.md`.
6. **`run_precheck`**, varprod refresh.
7. **`build_and_write_linearized`**.
8. Write **`rules_after_test_repair.json`**.

On compile failure: trace + prompt operator (retry REPAIR with compile error in payload — optional v1.1; v1: print error and return to gate without consuming round if compile fails before commit).

---

## Orchestration (`run.py`)

Replace flat tester block with:

```python
if with_tester:
    rules, meta, synth, z3_result, ok, issues, linearized, early = run_tester_interactive_loop(
        ...,
        with_test_repair=with_test_repair,
        interactive_tester=interactive_policy or interactive_tester,
        ...
    )
```

**New kwargs:**

| Flag | Default | Meaning |
|------|---------|---------|
| `--with-test-repair` | off | Allow Test-Repairer when interactive gate chooses REPAIR |
| `--interactive-tester` | off | Enable finding triage + gate even if `--interactive-policy` off |

**Constraints:**

- `--with-test-repair` requires `--with-tester`.
- `--with-test-repair` without interactive flag: print warning at startup; repair never runs (same as `--with-cross-repair` without interactive).

**`run_tester.py`:** add `--with-test-repair`, `--interactive-tester` / `--interactive-policy`.

**Outcomes:**

- `blocked_tester` — non-interactive + `--fail-on-tester-findings`, or interactive abort.
- `blocked_test_repair_compile` — repair produced rules that fail compile after retries (mirror `blocked_semantic_repair_compile`).
- `summary["tester_passed"]` — bool, true when last tester verdict `ok` or user `PROCEED_INCOMPLETE`.
- `summary["tester_repair_rounds"]` — int.

---

## CLI / operator examples

**Full e2e with triage + repair:**

```text
pivot-pipeline --input … --work-dir … --with-tester --with-test-repair --interactive-policy --with-critic …
```

**Replay on existing work_dir:**

```text
pivot-tester --work-dir … --input … --with-test-repair --interactive-tester
```

---

## Tests (v1)

| Test | Intent |
|------|--------|
| `test_tester_repair_handoff_filters_findings` | approved/ignored ids → handoff `findings` length |
| `test_finding_triage_approve_ignore` | mock `input_fn`: approve T001, ignore T002 → handoff |
| `test_run_test_repairer_mock_llm` | patches rules; `change_summary` references finding_id |
| `test_tester_loop_rerun_after_repair` | mock tester ok on second pass |
| `test_with_test_repair_requires_with_tester` | CLI parse error |

Use **`RepairerPivOutput`** validation fixtures; no live Gemini in unit tests.

---

## Documentation

- `ARCHITECTURE.md` — tester box → optional Test-Repairer loop + triage.
- `pivot_pipeline/README.md` — flags table.
- `dev_plan_pivot_tester_nl_linearized_alignment_v1.md` — link to this plan; note repair was follow-up.

---

## Non-goals (v1)

- Auto-repair without interactive triage.
- Repairing **ignored** findings anyway.
- Tester repair triggering **re-extract** from NL (rules JSON patch only).
- Separate repair agent for **NL text** changes (processed NL is read-only for repair).
- Merging Test-Repairer into Repairer_Piv (keep **bespoke prompt** for linearized alignment).

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Operator fatigue on many findings | Batch commands later (`approve all critical`); v1 per-finding is enough for ≤10 findings |
| Test-Repairer “fixes” benign PREEMPTION split | Prompt + ignore triage; recruitment-style `misalignment` → ignore |
| Compile break after repair | Same compile-attempt cap as semantic repair; do not advance `tester_repair_rounds` on failed compile |
| Drift between tester re-run and critic | After repair loop, critic still sees fresh `synthetic_en` from recompile |

---

## Done criteria (v1)

- [ ] `prompts/test_repairer.md` + `test_repairer_agent.py`
- [ ] `tester_interactive_loop.py` with per-finding approve/ignore + main gate
- [ ] `tester_repair_handoff.json` written; Test-Repairer sees approved findings only
- [ ] `--with-test-repair`, `--interactive-tester`; wired in `run.py` and `run_tester.py`
- [ ] Recompile / Z3 / linearize / **re-tester** after repair
- [ ] Unit tests for handoff filter + triage + mock repair
- [ ] ARCHITECTURE + README updated

---

## Follow-ups (v2+)

- **`approve critical`** / **`ignore warn`** bulk triage shortcuts.
- Compile-error-aware second Test-Repairer turn (pass validation error text).
- Non-interactive CI mode: `--fail-on-tester-findings` only (no repair).
- Persist triage choices in `tester_report.json` sidecar (`tester_triage.json`).
