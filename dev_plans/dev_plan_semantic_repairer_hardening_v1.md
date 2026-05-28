# Dev plan: Semantic Repairer_Piv hardening — registry loop, focused payload, triage, stall detection, routing

**Status:** Implemented  
**Priority:** P1 (recruitment `semantic_critic_loop` — registry JSON + full-policy Repairer_Piv retries burn budget; same failure fingerprints repeat)  
**Related run:** `NagV/exports/pivot_runs/recruitment_16_temp_wfm` — `repairer_piv_semantic_trace.jsonl`, `critic_drift_handoff.json`  
**Prerequisites (done):** `dev_plan_pivot_test_repairer_hardening_v1.md`, `dev_plan_cross_repairer_hardening_v1.md`, `dev_plan_cross_critic_finding_triage_v1.md`  
**Partial (done):** Unlimited user `REPAIR` sessions (`PIVOT_CRITIC_SEMANTIC_REPAIR_MAX=0`), API 503 no-burn retries, short gate after failed session — `semantic_critic_loop.py`

---

## 1. Problem (simple terms)

After **Pivot Critic** reports **DRIFT**, the operator types **`REPAIR`** to run **Repairer_Piv (semantic)**. The loop should patch IR, **compile**, refresh artifacts, and re-run the critic.

**What goes wrong today (representative, large policies):**

| Symptom | Actual stage | Why retries feel random |
|---------|--------------|-------------------------|
| `Registry after repair failed` … `line 66 column 24` (same char offset on retry) | **Registry LLM** JSON | Full **Repairer_Piv** re-invoked; registry error passed as `compile_validation_error` |
| `Repairer failed (repairer_json)` … `line 1466` | **Repairer** output parse | Full **37-rule** JSON re-emitted every attempt |
| `503 UNAVAILABLE` / `peer closed connection` | **API** | Burns attempts even with partial no-burn logic |
| Same CrossCritic findings after many `REPAIR`s | **No artifact write** | Compile/registry never both succeed |

**Structural gaps (semantic path vs hardened Test/Cross repair):**

1. **Order:** Registry runs **before** `load_rules_and_compile` — registry noise masks Pydantic errors; differs from Test/Cross (**pre-compile first**).
2. **Registry retry:** Uses single `registry_pass_from_nl_and_rules` — **not** `run_registry_pass_with_repairs` / `run_test_repair_registry` (JSON repair + slug-unchanged cache).
3. **Feedback:** Registry failures increment **repairer** attempt and set `compile_validation_error` — Repairer_Piv told to “fix rules” when **registry JSON** broke.
4. **Payload:** Full `rules` array every call — no `focus_rule_ids` / stubs / server merge.
5. **Scope:** Entire `critic_report.json` handoff every `REPAIR` — no per-finding triage on semantic critic (CrossCritic has triage; semantic does not).
6. **Routing:** Cross-rule wiring findings (R0034–R0037, obligation vs enforcement) sent to **semantic** Repairer_Piv, which rewrites broadly and triggers registry churn.
7. **Stall:** Identical error fingerprints repeat with no automated “stop burning attempts” signal (operator must infer manually).

**Non-goal:** Any workflow that requires **manual edit** of `rules_extracted.json`, registry files, or NL. Recovery is **retry**, **PROCEED_INCOMPLETE**, **narrower automated repair**, or **route to another automated agent** only.

---

## 2. Approved scope (five features)

Maps to operator-facing improvements **1–5** (no hand-repair paths).

| # | ID | One line |
|---|-----|----------|
| 1 | **S1** | Registry-only sub-loop — do not re-call Repairer_Piv when rules already compile |
| 2 | **S2** | Focused semantic payload + server merge (stubs for uncited rules) |
| 3 | **S3** | Critic finding triage — approve subset per `REPAIR` (like CrossCritic) |
| 4 | **S4** | Identical-error stall detection — stop session with clear automated guidance |
| 5 | **S5** | Repair routing — cross-family DRIFT → CrossRepairer path; semantic for true NL↔synthetic drift |

**Optional P2 (out of 1–5):** Exponential backoff on `repairer_api` / `registry_api`; separate env caps for repairer vs registry attempts (`S6`).

---

### S1 — Registry-only sub-loop + honest stage separation

**Problem:** One “compile attempt” = Repairer_Piv + registry + compile; registry/API failures waste Repairer calls; registry errors mislabeled as compile feedback.

**Design:**

1. **Reorder** semantic repair apply path to match Test/Cross:
   - Repairer_Piv → **merge** (after S2) → `sanitize` + **`precompile_repaired_rules`** (or `load_rules_and_compile` on merged rules only).
   - **Only if compile succeeds** → registry (`run_semantic_repair_registry` new helper, mirroring `run_test_repair_registry` / `run_cross_repair_registry`).
2. **Registry sub-loop** (inner):
   - Up to `PIVOT_CRITIC_SEMANTIC_REPAIR_REGISTRY_ATTEMPTS` (default **3**, clamp 1–10).
   - Use `registry_pass_from_nl_and_rules_with_repairs` + `PIVOT_REGISTRY_JSON_REPAIR_MAX`.
   - Reuse `can_reuse_cached_registry` / `apply_cached_registry` when slug set unchanged.
   - On registry failure: retry **registry only** with `registry_validation_error` prompt suffix — **do not** call Repairer_Piv again until registry cap exhausted.
3. **Outer loop** (per user `REPAIR`):
   - Up to `PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS` (default **5**) = **Repairer_Piv invocations** only (compile/merge failures).
   - Registry failures **do not** increment repairer attempt counter.
4. **Trace / handoff:** `critic_drift_handoff.json` fields:
   - `last_repair_error_stage`: `rules_compile` | `rules_merge` | `repairer_json` | `repairer_api` | `registry_json` | `registry_api`
   - `last_registry_error`, `last_compile_validation_error` (stage-appropriate).
5. **Terminal messages:** `Registry after repair failed` only when stage is registry; never prefix Repairer failure with “compile” when stage is `repairer_json`.

**Files:**

- `semantic_critic_loop.py` — refactor repair inner loops
- `semantic_repair_registry.py` (new, thin wrapper over `test_repair_registry.py` shared helpers)
- `repairer_piv_agent.py` — optional `registry_validation_error` suffix (or shared `registry_error_prompt_suffix.md`)

**Acceptance:**

- Unit test: repairer returns valid minimal rules, registry LLM raises `JSONDecodeError` twice then succeeds → **one** Repairer_Piv call, **three** registry tries, artifacts updated.
- Unit test: slug-unchanged repair → registry skipped, `identifier_registry.json` reused.

---

### S2 — Focused semantic payload + server merge

**Problem:** Repairer asked to re-emit entire policy (~1k+ lines JSON); parse errors at line 1400+.

**Design:**

1. Reuse `test_repair_rules_payload.py`:
   - `focus_rule_ids_from_critic_handoff(handoff)` — collect ids from `handoff.findings[]` (`rule_ids`, regex on explanation/recommendation), same as cross/test.
   - `build_rules_payload_stubs`, `merge_repairer_output` — **shared**.
2. Extend `run_repairer_piv_semantic`:
   - Payload: `focus_rule_ids`, stubbed `rules`.
   - After LLM: **server merge** into full policy before pre-compile.
3. Prompt:
   - New `prompts/semantic_repairer_ir_addendum.md` (or extend `repairer_piv_semantic.md`):
     - Output full `rules` array; **only edit** `focus_rule_ids`; echo stubs verbatim.
     - One finding → minimal edits; map `change_summary` to `finding_id` from critic handoff.
     - **No new `rule_id`** unless compile absolutely requires (rare).
     - Cross-link: do not nest `k_of_n` in `LOGICAL_IMPLICATION` triggers (reference shared normative doc).
   - Append addendum in `repairer_piv_agent._tmpl_semantic()` after `repairer_ir_normative.md`.
4. `MergeRepairerOutputError` handling — same retry path as Test/Cross (merge feedback, not compile feedback).

**Acceptance:**

- Fixture: 37 rules, focus 4 critic-cited ids → prompt `rules` section smaller than full dump; merge restores 37 rules; only focus ids differ.
- Regression: `test_repair_rules_payload` patterns reused; no duplicate merge logic.

---

### S3 — Semantic critic finding triage (subset per `REPAIR`)

**Problem:** Entire DRIFT report goes to Repairer_Piv every time; mixed-quality findings enlarge edits and registry churn.

**Design:**

1. New `semantic_critic_interactive_loop.py` helpers (mirror `cross_critic_interactive_loop.py`):
   - `run_critic_finding_triage(report, input_fn, print_fn)` → `approved_ids`, `ignored_ids`
   - Accept-all: `y` / `yes`
   - Selective: numbered list; user enters **disagree** indices (`2,3`)
   - `retriage` at gate re-runs triage
2. `critic_repair_handoff_dict()` — filtered `findings`, `approved_finding_ids`, `ignored_finding_ids`, `triage_index_map`, `full_report_path` → `critic_drift_handoff.json` (extend schema; bump `handoff_schema_version` to **1.1** if needed).
3. Gate flow (after DRIFT, before `REPAIR`):
   - Print triage summary (approved / ignored).
   - `REPAIR` with **zero approved** → hint; no LLM.
4. **Default UX:** On first DRIFT in a session, run triage once; sticky approved set across failed `REPAIR` retries until critic re-run passes or user `retriage` (same sticky pattern as tester resume).
5. Env: `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX_FINDINGS` (optional cap, 0 = no cap) — if set, warn when approved count exceeds cap and prompt to narrow (automated message only).

**Acceptance:**

- Test: three findings, user disagrees `2` → handoff contains only findings 1 and 3; Repairer payload `focus_rule_ids` derived from approved only.
- Test: `REPAIR` with zero approved → no `run_repairer_piv_semantic` call.

---

### S4 — Identical-error stall detection (automated, no hand-edit)

**Problem:** Same registry parse offset (`line 66 column 24`) or same repairer JSON error repeats; operator burns sessions without signal.

**Design:**

1. `repair_stall.py` (new) — `ErrorFingerprint` = `(stage, normalized_message)` where normalization strips attempt numbers and timestamps.
2. Per user `REPAIR` session, track last **K** fingerprints (default **3**).
3. If the same fingerprint appears **≥ 2** consecutive times at the **same stage**:
   - Print `[policy gate] Repair stalled: repeated <stage> error (automated).`
   - Message: suggest **`PROCEED_INCOMPLETE`**, wait and type **`REPAIR` again later**, or **`retriage`** to narrow findings — **never** mention manual file edit.
   - Optionally skip further LLM calls for remainder of **this** `REPAIR` session (fail fast).
4. Persist in `critic_drift_handoff.json`: `stall_detected: true`, `stall_fingerprint`, `stall_stage`.
5. Env: `PIVOT_SEMANTIC_REPAIR_STALL_THRESHOLD` (default **2**); `PIVOT_SEMANTIC_REPAIR_STALL_FAIL_FAST` (default **1**).

**Acceptance:**

- Test: registry returns same `Expecting ',' delimiter: line 66` twice → stall message; no third registry LLM call when fail-fast on.
- Test: different stages alternate → no stall (503 then registry ≠ stall unless same normalized message).

---

### S5 — Repair routing (cross-family DRIFT → CrossRepairer)

**Problem:** Findings about aggregate gates, obligation vs enforcement, escalation/status wiring are **cross-rule coherence**; semantic Repairer_Piv rewrites too much and fails registry/JSON.

**Design:**

1. `critic_finding_router.py` (new) — classify each `CriticFinding` (use `category`, `explanation`, `rule_ids`):
   - **`cross_coherence`** — keywords / patterns: `inconsistency`, `outcome_split`, `unreachable`, `aggregate`, `R0036`, `application_status`, `escalation`, `K_OF_N` linkage, multiple rule_ids across semantic families.
   - **`semantic_drift`** — NL vs synthetic mismatch, omission in synthetic index, pathway description, varprod excerpt alignment.
2. After critic DRIFT + triage (S3), print **routing summary**:
   - `Approved X001, X002 → recommended path: cross_coherence (--with-cross-critic already run?)`
   - `Approved C004 → semantic Repairer_Piv`
3. Gate behavior (when `with_cross_critic` + `with_cross_repair` + interactive):
   - If **all approved** findings classify as `cross_coherence`: print **block or strong defer** on semantic `REPAIR`:
     - “These findings are cross-rule IR coherence; run `pivot_pipeline.cross_coherence` (or continue cross slice) with CrossRepairer, not semantic Repairer_Piv.”
   - If **mixed**: print split; semantic `REPAIR` receives **only** `semantic_drift` findings in handoff; cross findings listed as “deferred to cross slice.”
   - Env override: `PIVOT_CRITIC_SEMANTIC_REPAIR_ALLOW_CROSS_FINDINGS=1` to allow semantic repair on cross-tagged findings anyway (default **0**).
4. **`run.py` integration:**
   - If operator is in **cross_coherence** slice and cross findings pending, prefer staying in cross loop (do not duplicate work in semantic loop).
   - Document in `README.md` / `ARCHITECTURE.md`: recommended order — cross coherence (triage + CrossRepairer) **before** waiving cross issues and relying on semantic DRIFT repair.
5. Optional: auto-populate `cross_repair_handoff.json` from critic approved cross findings when operator types `REPAIR` at critic gate and cross flags set — redirect to cross repair session (v1.1; can start with messaging-only in v1).

**Acceptance:**

- Test: handoff with only `inconsistency` / multi-rule aggregate finding → semantic `REPAIR` prints defer message; Repairer_Piv not called unless env override.
- Test: handoff with `omission` synthetic-only finding → semantic `REPAIR` proceeds.

---

## 3. Implementation order

| Phase | Items | Rationale |
|-------|--------|-----------|
| **P1a** | S1 registry sub-loop + stage labels | Stops mislabeled retries; biggest win for “registry line 66” loop |
| **P1b** | S2 focused payload + merge | Cuts repairer JSON size and parse failures |
| **P1c** | S4 stall detection | Protects operator time when provider/model stuck |
| **P2a** | S3 critic triage | Reduces scope per `REPAIR` |
| **P2b** | S5 routing + docs | Steers cross findings away from semantic repairer |

---

## 4. Environment variables (new / documented)

| Variable | Default | Purpose |
|----------|---------|---------|
| `PIVOT_CRITIC_SEMANTIC_REPAIR_REGISTRY_ATTEMPTS` | `3` | Registry-only tries per repairer success |
| `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX_FINDINGS` | `0` | Cap approved findings (0 = unlimited) |
| `PIVOT_SEMANTIC_REPAIR_STALL_THRESHOLD` | `2` | Repeated fingerprint count before stall |
| `PIVOT_SEMANTIC_REPAIR_STALL_FAIL_FAST` | `1` | Skip further LLM calls after stall in session |
| `PIVOT_CRITIC_SEMANTIC_REPAIR_ALLOW_CROSS_FINDINGS` | `0` | Allow semantic repair on cross-tagged findings |

Existing (document alongside): `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX`, `PIVOT_CRITIC_SEMANTIC_REPAIR_COMPILE_ATTEMPTS`, `PIVOT_CRITIC_SEMANTIC_REPAIR_COUNT_API_AS_ATTEMPT`, `PIVOT_REGISTRY_JSON_REPAIR_MAX`.

---

## 5. Tests

| Test module | Covers |
|-------------|--------|
| `test_semantic_repair_registry.py` | S1 slug skip, registry repair rounds, no repairer re-call |
| `test_semantic_repair_payload.py` | S2 focus/merge |
| `test_semantic_critic_triage.py` | S3 triage + filtered handoff |
| `test_repair_stall.py` | S4 fingerprint + fail-fast |
| `test_critic_finding_router.py` | S5 classification + gate defer |
| Extend `test_semantic_critic_loop.py` | End-to-end gate messages, stall, stage strings |

---

## 6. Documentation updates

- `NagV/pivot_pipeline/README.md` — semantic repair env table; routing order (cross before semantic for wiring findings).
- `NagV/pivot_pipeline/ARCHITECTURE.md` — semantic repair apply diagram (repairer → compile → registry).
- `dev_plan_pivot_repairer_tester_post_model_v1.md` — link to this plan; note `PIVOT_CRITIC_SEMANTIC_REPAIR_MAX` default **0**.

---

## 7. Success criteria (recruitment-class policies)

1. Registry JSON failure at attempt 1 does **not** trigger a full Repairer_Piv re-run at attempt 2 (unless compile also failed).
2. Repeated identical registry parse error triggers **stall message** within the same `REPAIR` session.
3. Semantic `REPAIR` on 4-rule critic focus emits merged policy that compiles; prompt size materially smaller than full rules dump.
4. Operator can approve **only X001** at critic triage; handoff and Repairer scope exclude X002.
5. Cross-tagged aggregate/wiring findings at critic gate print **defer to cross_coherence** when cross repair is enabled; no mandatory manual steps.

---

## 8. Out of scope

- Manual edit of rules, registry, or NL.
- New LLM provider / model selection UI (503 remains operational; backoff is P2).
- Replacing `PROCEED_INCOMPLETE` (still the waive path when automated repair exhausts).
