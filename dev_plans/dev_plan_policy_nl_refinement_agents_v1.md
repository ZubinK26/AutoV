# Dev plan: NL-aligned policy refinement (two-agent + SAT + critic repair)

## Purpose

Add a **post-formalization refinement stage** that uses **two LLM agents** (via API, same Gemini contract as WFM/SMT) to:

1. **Assess** the committed `policy_model.smt2` against the **canonical NL** in `agentsim/04_agentic_guardrails.md` (or another chosen source file).
2. **Return structured recommendations** identifying **where** in the SMT file to change and **why** (misalignment, vacuous axiom, wrong quantifier pattern, human-approval gap, sign/units, etc.).
3. **Apply** only those edits in a second step, with **inline comments** tying each edit to recommendation IDs.
4. **Verify and repair**: global **SAT check**, **Z3 parse** loop, and **semantic critic** loop until the refined file is syntactically valid, **SAT**, and critic-approved for the touched regions.

**Intent:** Automate what a careful human review would do after pipeline commit—tighten semantic alignment to NL, not rewrite policy from scratch.

**Non-goals (v1):** Full proof of equivalence NL↔SMT; automatic detection of all tautologies; replacing WFM or the chunk formalizer; running without human review of assessment JSON for high-stakes deploys.

---

## Roles and separation of concerns

| Role | Name in plan | Must not do |
|------|----------------|-------------|
| **Agent A — Assessor** | `PolicyAssessor` | Edit SMT-LIB; propose full-file rewrites; output patches |
| **Agent B — Implementer** | `PolicyImplementer` | Re-assess NL vs model; add new rules not backed by recommendations; remove recommendations |

**Hard rule:** Implementer input is **only** `(policy_smt2_text, nl_source_text, recommendations_json)` from the run record. No fresh web browse; no extra NL files unless passed in the manifest.

---

## Inputs and outputs

### Inputs (per run)

| Artifact | Description |
|----------|-------------|
| `policy_model.smt2` | Current monolithic policy (path). |
| `nl_source.md` | UTF-8, one rule per non-empty line (`#` comments ignored) — same contract as `nl_chunk_smt_policy_pipeline` / `parse_nl_rules`. |
| `run_manifest.json` (optional) | `policy_path`, `nl_path`, `provider_model`, `temperature`, caps, `run_id`. |

### Outputs (per run, under e.g. `exports/policy_refinement_runs/<run_id>/`)

| File | Description |
|------|-------------|
| `assessment.json` | Full assessor response metadata + **recommendations** array (normative schema below). |
| `implementation_request.json` | Copy of recommendations actually sent to implementer (+ optional `assessor_summary`). |
| `policy_refined.smt2` | Post-implementer SMT (before repair loop) OR overwritten in place after repair—see §7. |
| `repair_log.jsonl` | Parse / SAT / critic iterations (like bundle `*.log.jsonl`). |
| `final_report.json` | `sat_result`, `critic_final_approved`, `lines_touched_summary`, paths to artifacts. |

---

## Normative schema: assessor output

Assessor returns **exactly one JSON object** (no markdown fences). Top level:

```json
{
  "schema_version": "policy_refinement_assessment_v1",
  "run_id": "<opaque>",
  "nl_source_sha256": "<hex>",
  "policy_model_sha256_before": "<hex>",
  "summary": "<short human-readable summary>",
  "recommendations": [ … ],
  "no_changes_needed": false
}
```

**`recommendations[]` entry** (required fields):

| Field | Type | Meaning |
|-------|------|---------|
| `rec_id` | string | Stable within run, e.g. `REC-001` (implementer comments reference this). |
| `severity` | `"high"` \| `"medium"` \| `"low"` | Prioritize implementer + human triage. |
| `issue_type` | string | e.g. `nl_mismatch`, `vacuous_axiom`, `weakened_quantifier`, `missing_constraint`, `human_approval_gap`, `sign_units`, `duplicate_concept`, `other`. |
| `nl_evidence` | object | `{ "line_numbers": [int, …], "quoted_snippet": "…" }` — line numbers **1-based in nl_source.md after comment stripping** (implementation may send a numbered digest; see §5). |
| `policy_evidence` | object | **At least one** locator: `rule_id` (e.g. `r_9738387f5074`), and/or `line_range_1based` in `policy_model.smt2`, and/or `symbol` (declare-fun name). |
| `description` | string | What is wrong, in plain language. |
| `suggested_remediation` | string | Concrete direction (not necessarily full SMT): e.g. “Replace tautology with …”. |

**`no_changes_needed`:** If true, `recommendations` should be `[]` and downstream implementer is skipped.

---

## Normative schema: implementer output

Implementer returns **either**:

- **Preferred (v1):** A single JSON object:

```json
{
  "schema_version": "policy_refinement_implementation_v1",
  "rec_ids_addressed": ["REC-001", "REC-002"],
  "policy_smt2_full_text": "<entire file as UTF-8 string>",
  "edit_notes": [
    { "rec_id": "REC-001", "policy_line_start": 160, "policy_line_end": 175, "note": "…" }
  ]
}
```

- **Alternative (later):** unified diff — only if tooling applies diffs reliably; v1 standardizes on full file to avoid merge ambiguity.

**Comment convention (normative)** above any edited block:

```smt2
; --- REFINE rec_id=REC-001 | assessor: <one-line reason> ---
```

Do **not** remove existing `; Rule: …` headers; add refinement comments **adjacent** to changed asserts or declarations.

---

## Phase 1 — Prepare context for the assessor

1. Load `nl_source.md` and compute `nl_sha256`.
2. Load `policy_model.smt2` and compute `policy_sha256`.
3. Build **optional** `nl_numbered_digest`: non-comment lines prefixed with `NNN|` (1-based index matching `parse_nl_rules` order) to reduce assessor line-number drift. Include digest in the user payload below the raw file **or** as a separate tagged block.
4. Optionally truncate very large policies for **assessor** only with explicit “[TRUNCATED]” markers—**prefer** full-file for v1 until context limit hit; align with `SMT_PIPELINE_CONTEXT_CHAR_LIMIT` style env: `REFINEMENT_ASSESSOR_CONTEXT_CHAR_LIMIT` (default: same as SMT or 900k).

---

## Phase 2 — Assessor API call

- **System prompt:** `smt/policy_refinement/prompts/assessor_v1.md`
- **User message:** Tagged sections:
  - `<nl_source>` … `</nl_source>`
  - `<nl_numbered_digest>` … optional
  - `<policy_model_smt2>` … `</policy_model_smt2>`
  - `<task>` Produce JSON per schema … `</task>`
- **Model:** `GEMINI_MODEL` / temperature / max tokens — same as `wfm_orchestration` e2e defaults unless overridden in manifest.
- **Validation:** JSON parse; required fields present; each `rec_id` unique; every `policy_evidence` resolvable (rule id exists in file OR line range within file length).

**Failure handling:** If assessor returns invalid JSON or empty `recommendations` when obvious issues exist, **retry once** with “fix JSON only” nudge; then fail run with `ASSESSOR_MALFORMED`.

---

## Phase 3 — Implementer API call

- **System prompt:** `smt/policy_refinement/prompts/implementer_v1.md`
- **User message:**
  - `<recommendations_json>` … `</recommendations_json>`
  - `<policy_model_smt2>` … `</policy_model_smt2>`
  - Optionally `<nl_source>` excerpt only for quoted snippets referenced in recommendations (keep small).
- **Validation:** Output JSON parse; `policy_smt2_full_text` non-empty; `rec_ids_addressed` ⊆ assessor `rec_ids`; every addressed rec has at least one `REFINE` comment in the SMT text (soft check: grep `REFINE rec_id=`).

**Failure handling:** One repair retry if implementer omits schema fields; then `IMPLEMENTER_MALFORMED`.

---

## Phase 4 — SAT check (global)

1. Run **`analyze_policy_sat_and_core`** on `policy_smt2_full_text` (same as `smt_pipeline.policy_check` / post-commit gate).
2. **`sat`** → proceed to Phase 5.
3. **`unsat`** → Phase 6 (repair loop) with `failure_category: POLICY_UNSAT` + unsat core in log.
4. **`unknown`** → treat as **failure** for v1 (`POLICY_SAT_UNKNOWN`); optionally retry with different Z3 params (out of scope v1).

---

## Phase 5 — Parse check (whole file)

- `parse_smt2_string_check(full_text)` with `REFINEMENT_PARSE_TIMEOUT_SEC` (default: inherit `SMT_PIPELINE_PARSE_TIMEOUT_SEC`, e.g. 30s).
- If fail → Phase 6 with parser error string.

---

## Phase 6 — Repair loop (post-edit)

**Goal:** Recover **SAT + parse + semantic approval** without re-running assessor/implementer.

**Order:**  
1) **Syntax repair** (Z3 parse) — bounded iterations.  
2) **Global SAT** after each syntax-fixed candidate.  
3) **Semantic repair** — reuse **`smt_pipeline` critic** (`critic_v3.md`) on the **delta region**: packaging the changed bundle as a synthetic “proposed block” is awkward; **v1 simplification:** pass **full refined file** as `existing` and pass **only the concatenation of comment-tagged refined blocks** as `proposed` **or** critic sees (`before_snippet`, `after_snippet`) with explicit line ranges.

**Practical v1 approach (implementation detail for a follow-up PR):**

- Introduce `refinement_repair.py` that:
  - Extracts all regions between `; --- REFINE rec_id=` and the next `; Rule:` or `; ====` or EOF.
  - Builds `proposed_smt2_block` = concatenation of those regions.
  - `policy_text` = implementer output **minus** those regions replaced by placeholders **OR** critic receives full before/after in tags (see prompt tweak in `implementer_v1.md`: save `policy_before` in run dir).

**Critic:** Same JSON schema as pipeline (`approved`, `objections`). If not approved, call a small **repair formalizer** with `smt/policy_refinement/prompts/repair_formalizer_v1.md` (or reuse `formalizer_v3.md` with `<repair_mode>true</repair_mode>` and objections text) limited to **editing only the refined regions**.

**Budgets (defaults, overridable by env):**

| Setting | Default | Notes |
|---------|---------|--------|
| `REFINEMENT_SYNTAX_REPAIR_CAP` | `3` | Max parse-repair attempts |
| `REFINEMENT_SEMANTIC_REPAIR_CAP` | `3` | Max critic objection cycles |
| `REFINEMENT_MAX_RECOMMENDATIONS` | `50` | Assessor cap; excess dropped with warning |
| `REFINEMENT_IMPLEMENTER_MAX_OUTPUT_CHARS` | `policy_chars + 50_000` | Guardrail |
| `REFINEMENT_PARSE_TIMEOUT_SEC` | same as SMT | |

**Success criteria:** `parse_ok ∧ sat_result==sat ∧ critic.approved==true`.

If budgets exhausted: write `policy_refined_failed.smt2`, `final_report.json` status `failed`, **do not** overwrite canonical `policy_model.smt2` unless `--commit-refined` flag (future CLI).

---

## Phase 7 — Commit semantics (product decision)

- **Default:** Refined artifact lives only under `exports/policy_refinement_runs/…`.
- **Optional `--in-place`:** Replace input `policy_model.smt2` only after success + human confirmation flag (future).

---

## CLI sketch (future implementation)

```text
python -m smt.policy_refinement.cli assess-and-refine \
  --policy exports/.../policy_model.smt2 \
  --nl agentsim/04_agentic_guardrails.md \
  --out-dir exports/policy_refinement_runs/<run_id> \
  --skip-assessor  # optional: load existing assessment.json
```

This plan defines contracts and prompts; **implementation** is a separate small PR.

---

## Traceability and audit

- `assessment.json` is the **authoritative list of intents**.
- `policy_refined.smt2` must contain `; --- REFINE rec_id=…` comments for every implemented change.
- `final_report.json` links `rec_id` → line ranges in refined file + critic pass/fail history.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Assessor hallucinates line numbers | Numbered NL digest; validate rule_ids against file |
| Implementer drifts from NL | Implementer only allowed to close listed `rec_ids`; critic checks meaning |
| Repair loop widens edit scope | Repair formalizer prompt: “touch only lines inside REFINE blocks” |
| Context window | Optional digest + rule block extraction for assessor |

---

## Files delivered in this plan

| Path | Role |
|------|------|
| `dev_plans/dev_plan_policy_nl_refinement_agents_v1.md` | This document |
| `smt/policy_refinement/prompts/assessor_v1.md` | Assessor system prompt |
| `smt/policy_refinement/prompts/implementer_v1.md` | Implementer system prompt |
| `smt/policy_refinement/prompts/repair_formalizer_v1.md` | Post-edit parse/critic repair (minimal edits) |

**Future (implementation):** `smt/policy_refinement/cli.py`, `refinement_repair.py`, tests mirroring `smt_pipeline/tests`.

---

## Completion checklist (implementation phase)

- [ ] CLI loads policy + NL, calls assessor, writes `assessment.json`
- [ ] Calls implementer, validates comments + schema
- [ ] Global SAT + parse + critic repair with caps and logging
- [ ] Golden-file test on a tiny policy + intentional vacuous axiom
- [ ] Document env vars in `.env.example`
